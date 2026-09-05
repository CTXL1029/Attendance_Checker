import os
import fitz  # PyMuPDF
import subprocess
import copy  # Dùng để sao chép chuẩn XML của hàng mẫu
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

        # 1. Tính toán khoảng trống lề trên động giúp bảng luôn ở giữa trang
        top_padding_pt = max(20, 150 - (num_absent * 12))

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

        # 2. Xử lý Bảng điểm danh
        if doc.tables:
            table = doc.tables[0]
            table.alignment = WD_TABLE_ALIGNMENT.CENTER

            existing_data_rows = len(table.rows) - 1  # Trừ hàng tiêu đề

            # Trường hợp 1: Số vắng NHIỀU HƠN số hàng mẫu -> Nhân bản hàng mẫu (Index 1)
            if num_absent > existing_data_rows:
                template_tr = table.rows[1]._tr
                for _ in range(num_absent - existing_data_rows):
                    new_tr = copy.deepcopy(template_tr)
                    table._tbl.append(new_tr)

            # Trường hợp 2: Số vắng ÍT HƠN số hàng mẫu -> Xóa bớt hàng thừa từ cuối
            elif num_absent < existing_data_rows:
                while len(table.rows) - 1 > num_absent:
                    table._tbl.remove(table.rows[-1]._tr)

            # Điền dữ liệu và áp dụng định dạng đệm + font chuẩn cho TẤT CẢ các hàng
            for index, student in enumerate(data.absent_students, start=1):
                row = table.rows[index]
                cell_values = [
                    str(index),
                    student.name,
                    "Nghỉ có phép" if student.permission else ""
                ]

                for col_idx, text_val in enumerate(cell_values):
                    cell = row.cells[col_idx]
                    cell.text = ""  # Xóa text mặc định
                    p = cell.paragraphs[0]
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    
                    # Tạo khoảng đệm trên/dưới (padding) đồng nhất 8pt cho tất cả các hàng
                    p.paragraph_format.space_before = Pt(8)
                    p.paragraph_format.space_after = Pt(8)
                    
                    run = p.add_run(text_val)
                    run.font.name = "Mulish"
                    run.font.size = Pt(12)  # Cỡ chữ 12pt đồng nhất

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
        pix = page.get_pixmap(dpi=600)  # Chất lượng cao
        pix.save(output_png)
        pdf_doc.close()

        return FileResponse(output_png, media_type="image/png", filename=os.path.basename(output_png))

    except Exception as e:
        print("Lỗi Backend:", str(e))
        raise HTTPException(status_code=500, detail=str(e))