import os
import fitz  # PyMuPDF
import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT  # Bổ sung căn giữa cho Bảng
from docx.shared import Pt                       # Bổ sung căn khoảng cách pt

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
        num_absent = len(data.absent_students)

        # 1. Tính toán khoảng trống lề trên động (để thay thế căn giữa dọc của Word)
        # Trang ngang A4 có chiều cao ~595pt. Tùy số lượng học sinh vắng để đẩy tiêu đề xuống giữa trang.
        top_padding_pt = max(30, 160 - (num_absent * 15))

        for p in doc.paragraphs:
            if "Danh Sách Các Bạn Vắng Mặt" in p.text:
                p.paragraph_format.space_before = Pt(top_padding_pt)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in p.runs:
                    run.font.name = "Mulish"

            elif "Ngày dd/mm" in p.text:
                p.text = f"Ngày {data.date_str}"
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in p.runs:
                    run.font.name = "Mulish"

        # 2. Xử lý Bảng và Ép căn giữa khung bảng
        if doc.tables:
            table = doc.tables[0]
            
            # Bắt buộc căn giữa khung bảng theo chiều ngang trang giấy
            table.alignment = WD_TABLE_ALIGNMENT.CENTER

            # Xóa các hàng mẫu còn thừa từ Sample.docx
            while len(table.rows) - 1 > num_absent:
                row_to_remove = table.rows[-1]
                table._tbl.remove(row_to_remove._tr)

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

                # Điền nội dung + Ép căn giữa chữ + Ép Font Mulish cho từng ô
                for col_idx, text_val in enumerate(cell_values):
                    cell = row.cells[col_idx]
                    cell.text = ""
                    p = cell.paragraphs[0]
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    
                    run = p.add_run(text_val)
                    run.font.name = "Mulish"

        # Lưu tệp docx tạm thời
        output_docx = f"/tmp/output_{data.date_full}.docx"
        output_pdf_dir = "/tmp"
        output_pdf = f"/tmp/output_{data.date_full}.pdf"
        output_png = f"/tmp/Attendance_Checker_{data.class_name}_{data.date_full}.png"

        doc.save(output_docx)

        # 3. Chuyển đổi DOCX -> PDF
        subprocess.run([
            "soffice", "--headless", "--convert-to", "pdf",
            output_docx, "--outdir", output_pdf_dir
        ], check=True)

        # 4. Chuyển đổi PDF -> PNG
        pdf_doc = fitz.open(output_pdf)
        page = pdf_doc[0]
        pix = page.get_pixmap(dpi=600)
        pix.save(output_png)
        pdf_doc.close()

        return FileResponse(output_png, media_type="image/png", filename=os.path.basename(output_png))

    except Exception as e:
        print("Lỗi Backend:", str(e))
        raise HTTPException(status_code=500, detail=str(e))