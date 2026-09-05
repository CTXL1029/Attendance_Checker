import os
import fitz  # PyMuPDF
import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH  # Import module hỗ trợ căn lề

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AbsentStudent(BaseModel):
    name: str
    permission: bool

class AttendanceRequest(BaseModel):
    class_name: str
    date_str: str       # dd/mm
    date_full: str      # dd-mm-yyyy
    absent_students: list[AbsentStudent]

@app.post("/api/process-attendance")
def process_attendance(data: AttendanceRequest):
    try:
        template_path = os.path.join(os.path.dirname(__file__), "Sample.docx")
        if not os.path.exists(template_path):
            raise HTTPException(status_code=500, detail="Thiếu tệp mẫu Sample.docx")

        doc = Document(template_path)

        # 1. Cập nhật ngày xử lý (Giữ căn giữa & Font Mulish)
        for p in doc.paragraphs:
            if "Ngày dd/mm" in p.text:
                p.text = f"Ngày {data.date_str}"
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in p.runs:
                    run.font.name = "Mulish"

        # 2. Xử lý Bảng điểm danh
        if doc.tables:
            table = doc.tables[0]
            num_absent = len(data.absent_students)

            # Xóa các hàng trống thừa còn dư từ file Sample.docx
            # (Hàng 0 là tiêu đề, các hàng từ index 1 trở đi là dữ liệu)
            while len(table.rows) - 1 > num_absent:
                row_to_remove = table.rows[-1]
                tr = row_to_remove._tr
                table._tbl.remove(tr)

            # Điền dữ liệu học sinh vắng
            for index, student in enumerate(data.absent_students, start=1):
                if index < len(table.rows):
                    row = table.rows[index]
                else:
                    row = table.add_row()

                cell_values = [
                    str(index),
                    student.name,
                    "Nghỉ có phép" if student.permission else ""
                ]

                # Ghi dữ liệu vào từng ô và ép căn giữa + Font Mulish
                for col_idx, text_val in enumerate(cell_values):
                    cell = row.cells[col_idx]
                    cell.text = ""  # Xóa text mặc định
                    p = cell.paragraphs[0]
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER  # Ép căn giữa ô
                    
                    run = p.add_run(text_val)
                    run.font.name = "Mulish"                  # Ép font Mulish

        # Lưu tệp docx tạm thời
        output_docx = f"/tmp/output_{data.date_full}.docx"
        output_pdf_dir = "/tmp"
        output_pdf = f"/tmp/output_{data.date_full}.pdf"
        output_png = f"/tmp/Attendance_Checker_{data.class_name}_{data.date_full}.png"

        doc.save(output_docx)

        # 3. Chuyển đổi DOCX -> PDF bằng LibreOffice
        subprocess.run([
            "soffice", "--headless", "--convert-to", "pdf",
            output_docx, "--outdir", output_pdf_dir
        ], check=True)

        # 4. Chuyển đổi PDF -> PNG bằng PyMuPDF
        pdf_doc = fitz.open(output_pdf)
        page = pdf_doc[0]
        pix = page.get_pixmap(dpi=600)
        pix.save(output_png)
        pdf_doc.close()

        return FileResponse(output_png, media_type="image/png", filename=os.path.basename(output_png))

    except Exception as e:
        print("Lỗi Backend:", str(e))
        raise HTTPException(status_code=500, detail=str(e))