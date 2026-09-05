import os
import fitz  # PyMuPDF
import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from docx import Document

app = FastAPI()

# Bật CORS cho phép GitHub Pages truy cập
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

        # 1. Cập nhật ngày xử lý trong văn bản
        for p in doc.paragraphs:
            if "Ngày dd/mm" in p.text:
                p.text = p.text.replace("Ngày dd/mm", f"Ngày {data.date_str}")

        # 2. Điền danh sách vắng vào bảng
        if doc.tables:
            table = doc.tables[0]
            
            for index, student in enumerate(data.absent_students, start=1):
                # Thêm hàng mới nếu số học sinh nhiều hơn hàng mẫu trong docx
                if index < len(table.rows):
                    row_cells = table.rows[index].cells
                else:
                    row_cells = table.add_row().cells

                row_cells[0].text = str(index)
                row_cells[1].text = student.name
                row_cells[2].text = "Nghỉ có phép" if student.permission else ""

        # Lưu tệp docx tạm thời
        output_docx = f"/tmp/output_{data.date_full}.docx"
        output_pdf_dir = "/tmp"
        output_pdf = f"/tmp/output_{data.date_full}.pdf"
        output_png = f"/tmp/Attendance_Checker_{data.class_name}_{data.date_full}.png"

        doc.save(output_docx)

        # 3. Sử dụng LibreOffice chuyển đổi DOCX -> PDF
        subprocess.run([
            "soffice", "--headless", "--convert-to", "pdf",
            output_docx, "--outdir", output_pdf_dir
        ], check=True)

        # 4. Sử dụng PyMuPDF (fitz) chuyển PDF -> PNG
        pdf_doc = fitz.open(output_pdf)
        page = pdf_doc[0]
        pix = page.get_pixmap(dpi=150)
        pix.save(output_png)
        pdf_doc.close()

        return FileResponse(output_png, media_type="image/png", filename=os.path.basename(output_png))

    except Exception as e:
        print("Lỗi Backend:", str(e))
        raise HTTPException(status_code=500, detail=str(e))