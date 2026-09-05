import os
import fitz  # PyMuPDF
import subprocess
import copy
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Pt

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

        # 1. Ép cố định lề trang (Margins = 0.5 inch = 36pt) để cân bằng trang giấy A4 ngang (595pt)
        section = doc.sections[0]
        section.top_margin = Pt(36)
        section.bottom_margin = Pt(36)
        section.left_margin = Pt(36)
        section.right_margin = Pt(36)

        # 2. Công thức tính toán chính xác khoảng lề trên để toàn bộ khối nội dung nằm giữa trang
        top_space_pt = max(10, int(215 - (12 * num_absent)))

        for p in doc.paragraphs:
            if "Danh Sách Các Bạn Vắng Mặt" in p.text:
                p.paragraph_format.space_before = Pt(top_space_pt)
                p.paragraph_format.space_after = Pt(4)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in p.runs:
                    run.font.name = "Mulish"

            elif "Ngày dd/mm" in p.text:
                p.text = f"Ngày {data.date_str}"
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(16)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in p.runs:
                    run.font.name = "Mulish"

        # 3. Xử lý Bảng điểm danh
        if doc.tables:
            table = doc.tables[0]
            table.alignment = WD_TABLE_ALIGNMENT.CENTER

            existing_data_rows = len(table.rows) - 1  # Trừ hàng tiêu đề

            # Thêm hoặc xóa hàng để vừa đúng số lượng học sinh vắng
            if num_absent > existing_data_rows:
                template_tr = table.rows[1]._tr
                for _ in range(num_absent - existing_data_rows):
                    new_tr = copy.deepcopy(template_tr)
                    table._tbl.append(new_tr)
            elif num_absent < existing_data_rows:
                while len(table.rows) - 1 > num_absent:
                    table._tbl.remove(table.rows[-1]._tr)

            # Định dạng lại hàng tiêu đề (Hàng 0)
            for cell in table.rows[0].cells:
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(6)
                p.paragraph_format.space_after = Pt(6)
                for run in p.runs:
                    run.font.name = "Mulish"

            # Điền dữ liệu và định dạng hàng dữ liệu (Hàng 1 -> N)
            for index, student in enumerate(data.absent_students, start=1):
                row = table.rows[index]
                cell_values = [
                    str(index),
                    student.name,
                    "Nghỉ có phép" if student.permission else ""
                ]

                for col_idx, text_val in enumerate(cell_values):
                    cell = row.cells[col_idx]
                    cell.text = ""
                    p = cell.paragraphs[0]
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    
                    # Khoảng đệm đều 6pt trên/dưới mỗi dòng
                    p.paragraph_format.space_before = Pt(6)
                    p.paragraph_format.space_after = Pt(6)
                    
                    run = p.add_run(text_val)
                    run.font.name = "Mulish"
                    run.font.size = Pt(12)

        # Lưu tệp docx tạm thời
        output_docx = f"/tmp/output_{data.date_full}.docx"
        output_pdf_dir = "/tmp"
        output_pdf = f"/tmp/output_{data.date_full}.pdf"
        output_png = f"/tmp/Attendance_Checker_{data.class_name}_{data.date_full}.png"

        doc.save(output_docx)

        # 4. Chuyển đổi sang PDF
        subprocess.run([
            "soffice", "--headless", "--convert-to", "pdf",
            output_docx, "--outdir", output_pdf_dir
        ], check=True)

        # 5. Chuyển đổi PDF sang PNG
        pdf_doc = fitz.open(output_pdf)
        page = pdf_doc[0]
        pix = page.get_pixmap(dpi=600)
        pix.save(output_png)
        pdf_doc.close()

        return FileResponse(output_png, media_type="image/png", filename=os.path.basename(output_png))

    except Exception as e:
        print("Lỗi Backend:", str(e))
        raise HTTPException(status_code=500, detail=str(e))