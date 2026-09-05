// CẤU HÌNH RENDER BACKEND URL
const BACKEND_URL = "https://your-render-service-name.onrender.com"; // Thay URL Render của bạn vào đây

// GitHub Repository Info dùng để đọc động thư mục lists/
const GITHUB_USER = "CTXL1029"; // Thay username GitHub
const GITHUB_REPO = "Attendance_Checker"; // Thay tên repo

let state = {
  date: "",
  selectedClass: "K60G",
  classLists: {}, // { 'K60G': [{id, name, checked, permission}], ... }
  collapsibleOpen: false,
};

let generatedBlob = null;
let generatedFileName = "";

document.addEventListener("DOMContentLoaded", async () => {
  initDateAndStorage();
  await loadClassLists();
  setupEventListeners();
  render();
});

// 1. Quản lý Bộ nhớ và Tự động Reset theo ngày
function initDateAndStorage() {
  const today = new Date().toISOString().split("T")[0];
  const savedState = localStorage.getItem("attendance_app_state");

  if (savedState) {
    const parsed = JSON.parse(savedState);
    if (parsed.date === today) {
      state = parsed;
      return;
    }
  }

  // Ngày mới hoặc chưa có dữ liệu -> Khởi tạo lại
  state.date = today;
  state.classLists = {};
  saveState();
}

function saveState() {
  localStorage.setItem("attendance_app_state", JSON.stringify(state));
}

// 2. Đọc danh sách lớp từ folder /lists
async function loadClassLists() {
  try {
    // Gọi GitHub API để lấy các tệp trong folder lists
    const response = await fetch(
      `https://api.github.com/repos/${GITHUB_USER}/${GITHUB_REPO}/contents/lists`,
    );
    const files = await response.json();

    const txtFiles = Array.isArray(files)
      ? files.filter((f) => f.name.endsWith(".txt"))
      : [
          { name: "K60G.txt", path: "lists/K60G.txt" },
          { name: "Toán-Chiều.txt", path: "lists/Toán-Chiều.txt" },
        ];

    const selectEl = document.getElementById("classSelect");
    selectEl.innerHTML = "";

    for (const file of txtFiles) {
      const className = file.name.replace(".txt", "");
      const option = document.createElement("option");
      option.value = className;
      option.textContent = className;
      selectEl.appendChild(option);

      // Nếu chưa có dữ liệu lớp này trong state thì tải nội dung file
      if (!state.classLists[className]) {
        const fileRes = await fetch(`./lists/${file.name}`);
        const text = await fileRes.text();
        const names = text
          .split("\n")
          .map((n) => n.trim())
          .filter((n) => n.length > 0);

        state.classLists[className] = names.map((name, index) => ({
          id: index + 1,
          name: name,
          checked: false,
          permission: false,
        }));
      }
    }

    if (!state.selectedClass || !state.classLists[state.selectedClass]) {
      state.selectedClass = "K60G";
    }
    selectEl.value = state.selectedClass;
    saveState();
  } catch (err) {
    console.error("Lỗi tải danh sách lớp:", err);
  }
}

// 3. Render Giao diện
function render() {
  const list = state.classLists[state.selectedClass] || [];

  const mainTableBody = document.getElementById("mainTableBody");
  const checkedTableBody = document.getElementById("checkedTableBody");

  mainTableBody.innerHTML = "";
  checkedTableBody.innerHTML = "";

  let checkedCount = 0;

  list.forEach((item, index) => {
    const tr = document.createElement("tr");

    if (!item.checked) {
      // Hàng ở Bảng chính
      tr.innerHTML = `
        <td><input type="checkbox" onchange="toggleCheck(${index}, true)"></td>
        <td style="text-align: left; padding-left: 12px;">${item.name}</td>
        <td><input type="checkbox" ${item.permission ? "checked" : ""} onchange="togglePermission(${index}, this.checked)"></td>
      `;
      mainTableBody.appendChild(tr);
    } else {
      // Hàng ở Bảng đã điểm danh
      checkedCount++;
      tr.innerHTML = `
        <td><input type="checkbox" checked onchange="toggleCheck(${index}, false)"></td>
        <td style="text-align: left; padding-left: 12px; text-decoration: line-through; color: #777;">${item.name}</td>
        <td><input type="checkbox" ${item.permission ? "checked" : ""} disabled></td>
      `;
      checkedTableBody.appendChild(tr);
    }
  });

  document.getElementById("checkedCount").textContent = checkedCount;

  // Collapse state
  const collapsibleContent = document.getElementById("collapsibleContent");
  const arrowIcon = document.getElementById("arrowIcon");
  if (state.collapsibleOpen) {
    collapsibleContent.classList.remove("hidden");
    arrowIcon.style.transform = "rotate(180deg)";
  } else {
    collapsibleContent.classList.add("hidden");
    arrowIcon.style.transform = "rotate(0deg)";
  }
}

// Global Handlers cho DOM Events
window.toggleCheck = (index, status) => {
  state.classLists[state.selectedClass][index].checked = status;
  saveState();
  render();
};

window.togglePermission = (index, status) => {
  state.classLists[state.selectedClass][index].permission = status;
  saveState();
};

function setupEventListeners() {
  document.getElementById("classSelect").addEventListener("change", (e) => {
    state.selectedClass = e.target.value;
    saveState();
    render();
  });

  document.getElementById("toggleCollapse").addEventListener("click", () => {
    state.collapsibleOpen = !state.collapsibleOpen;
    saveState();
    render();
  });

  document.getElementById("btnReset").addEventListener("click", () => {
    if (confirm("Bạn có chắc chắn muốn đặt lại bảng điểm danh lớp này?")) {
      const list = state.classLists[state.selectedClass];
      if (list) {
        list.forEach((item) => {
          item.checked = false;
          item.permission = false;
        });
      }
      saveState();
      render();
    }
  });

  // Xuất & Xử lý Pop-up Modal
  document
    .getElementById("btnExport")
    .addEventListener("click", handleExportClick);
  document.getElementById("btnCloseModal").addEventListener("click", () => {
    document.getElementById("exportModal").classList.add("hidden");
  });
}

// 4. Logic Xử lý Xuất / Render Backend
async function handleExportClick() {
  const list = state.classLists[state.selectedClass] || [];
  const absentList = list.filter((item) => !item.checked);

  const modal = document.getElementById("exportModal");
  const btnSaveImage = document.getElementById("btnSaveImage");
  const modalStatus = document.getElementById("modalStatusText");

  modal.classList.remove("hidden");
  generatedBlob = null;

  const now = new Date();
  const dd = String(now.getDate()).padStart(2, "0");
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const yyyy = now.getFullYear();

  if (absentList.length === 0) {
    // Trường hợp ĐẾN ĐỦ -> Không qua Render xử lý
    btnSaveImage.disabled = true;
    modalStatus.textContent = "Lớp đi học đầy đủ!";

    document.getElementById("btnShare").onclick = () => {
      const msg = `[Ngày ${dd}/${mm}]\nLớp trưởng thông báo: Hiện tại lớp đủ\n@All`;
      if (navigator.share) {
        navigator.share({ text: msg });
      } else {
        navigator.clipboard.writeText(msg);
        alert("Đã sao chép tin nhắn vào bộ nhớ tạm!");
      }
    };
  } else {
    // Trường hợp VẮNG -> Gửi sang Backend Python
    btnSaveImage.disabled = false;
    modalStatus.textContent = "Đang tạo ảnh điểm danh từ máy chủ Backend...";

    const payload = {
      class_name: state.selectedClass,
      date_str: `${dd}/${mm}`,
      date_full: `${dd}-${mm}-${yyyy}`,
      absent_students: absentList.map((a) => ({
        name: a.name,
        permission: a.permission,
      })),
    };

    try {
      const response = await fetch(`${BACKEND_URL}/api/process-attendance`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error("Lỗi khi kết nối Backend");

      generatedBlob = await response.blob();
      generatedFileName = `Attendance_Checker_${state.selectedClass}_${dd}-${mm}-${yyyy}.png`;
      modalStatus.textContent = "Đã chuẩn bị xong hình ảnh!";

      // Nút Lưu ảnh
      btnSaveImage.onclick = () => {
        const url = window.URL.createObjectURL(generatedBlob);
        const a = document.createElement("a");
        a.href = url;
        a.download = generatedFileName;
        a.click();
      };

      // Nút Chia sẻ
      document.getElementById("btnShare").onclick = async () => {
        const shareText = `[Ngày ${dd}/${mm}]\nLớp trưởng thông báo: Hiện tại lớp vắng ${absentList.length} bạn như trong danh sách\n@All`;
        const file = new File([generatedBlob], generatedFileName, {
          type: "image/png",
        });

        if (navigator.canShare && navigator.canShare({ files: [file] })) {
          await navigator.share({
            files: [file],
            text: shareText,
          });
        } else if (navigator.share) {
          await navigator.share({ text: shareText });
        } else {
          navigator.clipboard.writeText(shareText);
          alert("Đã sao chép tin nhắn!");
        }
      };
    } catch (err) {
      console.error(err);
      modalStatus.textContent = "Không thể kết nối đến server Render!";
    }
  }
}
