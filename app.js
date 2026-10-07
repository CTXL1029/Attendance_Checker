const GITHUB_USER = "CTXL1029";
const GITHUB_REPO = "Attendance_Checker";

let state = {
  sessionKey: "",
  isAfternoon: false,
  selectedClass: "K60G",
  classLists: {},
  collapsibleOpen: false,
};

let generatedBlob = null;
let generatedFileName = "";

document.addEventListener("DOMContentLoaded", async () => {
  initDateAndStorage();
  await loadClassLists();
  setupEventListeners();
  render();

  // Tự động kiểm tra và cập nhật ca khi người dùng mở lại tab (hữu ích cho PWA)
  document.addEventListener("visibilitychange", async () => {
    if (document.visibilityState === "visible") {
      if (initDateAndStorage()) {
        await loadClassLists();
        render();
      }
    }
  });

  // Kiểm tra định kỳ mỗi phút phòng khi người dùng treo máy và vượt qua 12h trưa
  setInterval(async () => {
    if (initDateAndStorage()) {
      await loadClassLists();
      render();
    }
  }, 60000);
});

function initDateAndStorage() {
  const now = new Date();

  // Đã sửa lỗi: Lấy ngày theo giờ địa phương thay vì toISOString() để tránh lệch múi giờ
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const date = String(now.getDate()).padStart(2, "0");
  const today = `${year}-${month}-${date}`;

  const hour = now.getHours();
  const period = hour < 12 ? "AM" : "PM";
  const currentSessionKey = `${today}-${period}`;

  const savedState = localStorage.getItem("attendance_app_state");
  if (savedState) {
    const parsed = JSON.parse(savedState);
    if (parsed.sessionKey === currentSessionKey) {
      state = parsed;
      return false; // Trạng thái vẫn là ca hiện tại (sáng hoặc chiều)
    }
    // Giữ lại tên lớp đang chọn khi ứng dụng tự động chuyển sang ca mới
    if (parsed.selectedClass) state.selectedClass = parsed.selectedClass;
    if (parsed.collapsibleOpen !== undefined)
      state.collapsibleOpen = parsed.collapsibleOpen;
  }

  // Đã sửa lỗi: Xoá bỏ ngoại lệ thứ 3, thứ 4. Bây giờ cứ đúng >= 12h thì mới mặc định tick chiều.
  let defaultIsAfternoon = hour >= 12;

  state.sessionKey = currentSessionKey;
  state.isAfternoon = defaultIsAfternoon;
  state.classLists = {};
  saveState();
  return true; // Báo hiệu đã sang ca mới để reset list
}

function saveState() {
  localStorage.setItem("attendance_app_state", JSON.stringify(state));
}

async function loadClassLists() {
  let masterLists =
    JSON.parse(localStorage.getItem("master_class_lists")) || {};
  let txtFiles = [];

  try {
    const response = await fetch(
      `https://api.github.com/repos/${GITHUB_USER}/${GITHUB_REPO}/contents/lists`,
    );
    if (!response.ok) throw new Error("Mất kết nối mạng");
    const files = await response.json();
    txtFiles = files.filter((f) => f.name.endsWith(".txt"));
  } catch (err) {
    console.warn("Đang chạy Offline. Dùng danh sách từ bộ nhớ đệm.");
    txtFiles = Object.keys(masterLists).map((name) => ({
      name: `${name}.txt`,
    }));
  }

  const selectEl = document.getElementById("classSelect");
  selectEl.innerHTML = "";

  for (const file of txtFiles) {
    const className = file.name.replace(".txt", "");
    const option = document.createElement("option");
    option.value = className;
    option.textContent = className;
    selectEl.appendChild(option);

    try {
      const fileRes = await fetch(
        `./lists/${file.name}?v=${new Date().getTime()}`,
      );
      if (!fileRes.ok) throw new Error("Không tải được file");
      const text = await fileRes.text();
      const names = text
        .split("\n")
        .map((n) => n.trim())
        .filter((n) => n.length > 0);
      masterLists[className] = names;
    } catch (err) {}

    if (!state.classLists[className] && masterLists[className]) {
      state.classLists[className] = masterLists[className].map(
        (name, index) => ({
          id: index + 1,
          name: name,
          checked: false,
          permission: false,
        }),
      );
    }
  }

  localStorage.setItem("master_class_lists", JSON.stringify(masterLists));

  if (!state.selectedClass || !state.classLists[state.selectedClass]) {
    state.selectedClass =
      selectEl.options.length > 0 ? selectEl.options[0].value : "K60G";
  }
  selectEl.value = state.selectedClass;
  saveState();
}

function render() {
  document.getElementById("chkAfternoon").checked = state.isAfternoon;
  const list = state.classLists[state.selectedClass] || [];
  const mainTableBody = document.getElementById("mainTableBody");
  const checkedTableBody = document.getElementById("checkedTableBody");

  mainTableBody.innerHTML = "";
  checkedTableBody.innerHTML = "";
  let checkedCount = 0;

  list.forEach((item, index) => {
    const tr = document.createElement("tr");
    if (!item.checked) {
      tr.innerHTML = `
        <td><input type="checkbox" onchange="toggleCheck(${index}, true)"></td>
        <td style="text-align: left; padding-left: 12px;">${item.name}</td>
        <td><input type="checkbox" ${item.permission ? "checked" : ""} onchange="togglePermission(${index}, this.checked)"></td>
      `;
      mainTableBody.appendChild(tr);
    } else {
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
  document.getElementById("chkAfternoon").addEventListener("change", (e) => {
    state.isAfternoon = e.target.checked;
    saveState();
  });
  document.getElementById("toggleCollapse").addEventListener("click", () => {
    state.collapsibleOpen = !state.collapsibleOpen;
    saveState();
    render();
  });
  document.getElementById("btnReset").addEventListener("click", () => {
    if (confirm("Bạn có chắc chắn muốn đặt lại bảng điểm danh lớp này?")) {
      const list = state.classLists[state.selectedClass];
      if (list)
        list.forEach((item) => {
          item.checked = false;
          item.permission = false;
        });
      saveState();
      render();
    }
  });
  document
    .getElementById("btnExport")
    .addEventListener("click", handleExportClick);
  document.getElementById("btnCloseModal").addEventListener("click", () => {
    document.getElementById("exportModal").classList.add("hidden");
  });
}

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
  const sessionTitle = state.isAfternoon
    ? `[Chiều Ngày ${dd}/${mm}]`
    : `[Sáng - Ngày ${dd}/${mm}]`;

  if (absentList.length === 0) {
    btnSaveImage.disabled = true;
    modalStatus.textContent = "Lớp đi học đầy đủ!";
    document.getElementById("btnShare").onclick = () => {
      const msg = `${sessionTitle}\nLớp trưởng thông báo: Hiện tại lớp đủ`;
      if (navigator.share) navigator.share({ text: msg });
      else {
        navigator.clipboard.writeText(msg);
        alert("Đã sao chép tin nhắn vào bộ nhớ tạm!");
      }
    };
  } else {
    btnSaveImage.disabled = false;
    modalStatus.textContent = "Đang xử lý ảnh trên máy của bạn...";

    document.getElementById("templateDate").textContent = `Ngày ${dd}/${mm}`;
    const tbody = document.getElementById("templateTableBody");
    tbody.innerHTML = "";

    absentList.forEach((student, idx) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${idx + 1}</td>
        <td style="text-align: left; padding-left: 20px; font-weight: 600;">${student.name}</td>
        <td>${student.permission ? "Nghỉ có phép" : ""}</td>
      `;
      tbody.appendChild(tr);
    });

    try {
      const templateEl = document.getElementById("exportTemplate");
      const canvas = await html2canvas(templateEl, {
        scale: 6,
        backgroundColor: "#ffffff",
        logging: false,
        useCORS: true,
      });

      canvas.toBlob(async (blob) => {
        generatedBlob = blob;
        generatedFileName = `Attendance_Checker_${state.selectedClass}_${dd}-${mm}-${yyyy}.png`;
        modalStatus.textContent = "Đã xuất xong hình ảnh!";

        btnSaveImage.onclick = () => {
          const url = window.URL.createObjectURL(generatedBlob);
          const a = document.createElement("a");
          a.href = url;
          a.download = generatedFileName;
          a.click();
        };

        document.getElementById("btnShare").onclick = async () => {
          const shareText = `${sessionTitle}\nLớp trưởng thông báo:\nHiện tại lớp vắng ${absentList.length} bạn như trong danh sách`;
          const file = new File([generatedBlob], generatedFileName, {
            type: "image/png",
          });
          if (navigator.canShare && navigator.canShare({ files: [file] })) {
            await navigator.share({ files: [file], text: shareText });
          } else if (navigator.share) {
            await navigator.share({ text: shareText });
          } else {
            navigator.clipboard.writeText(shareText);
            alert(
              "Trình duyệt không hỗ trợ Share Ảnh. Đã sao chép nội dung văn bản!",
            );
          }
        };
      }, "image/png");
    } catch (err) {
      console.error(err);
      modalStatus.textContent = "Có lỗi xảy ra khi tạo ảnh!";
    }
  }
}
