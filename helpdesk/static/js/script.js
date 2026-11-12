```javascript
document.addEventListener("DOMContentLoaded", function () {

    // Mobile sidebar toggle
    const sidebar = document.getElementById("sidebar");
    const menuToggle = document.getElementById("menuToggle");

    if (sidebar && menuToggle) {
        menuToggle.addEventListener("click", function () {
            sidebar.classList.toggle("open");
        });

        document.addEventListener("click", function (event) {
            const clickedInsideSidebar = sidebar.contains(event.target);
            const clickedToggle = menuToggle.contains(event.target);

            if (
                window.innerWidth <= 700 &&
                !clickedInsideSidebar &&
                !clickedToggle
            ) {
                sidebar.classList.remove("open");
            }
        });
    }

    // Task filtering
    const filterButtons = document.querySelectorAll(".filter-button");
    const taskRows = document.querySelectorAll("#taskTable tbody tr");
    const emptyState = document.getElementById("emptyState");

    let currentFilter = "all";
    let currentSearch = "";

    function filterTasks() {
        let visibleCount = 0;

        taskRows.forEach(function (row) {
            const status = row.dataset.status || "";
            const text = row.textContent.toLowerCase();

            const matchesFilter =
                currentFilter === "all" || status === currentFilter;

            const matchesSearch = text.includes(currentSearch);

            const shouldShow = matchesFilter && matchesSearch;

            row.hidden = !shouldShow;

            if (shouldShow) {
                visibleCount++;
            }
        });

        if (emptyState) {
            emptyState.hidden = visibleCount !== 0;
        }
    }

    filterButtons.forEach(function (button) {
        button.addEventListener("click", function () {

            filterButtons.forEach(function (item) {
                item.classList.remove("active");
            });

            button.classList.add("active");
            currentFilter = button.dataset.filter || "all";

            filterTasks();
        });
    });

    // Search tasks
    const globalSearch = document.getElementById("globalSearch");

    if (globalSearch) {
        globalSearch.addEventListener("input", function () {
            currentSearch = globalSearch.value.trim().toLowerCase();
            filterTasks();
        });
    }

    // Create task button
    const createTaskBtn = document.getElementById("createTaskBtn");

    if (createTaskBtn) {
        createTaskBtn.addEventListener("click", function () {
            alert(
                "Create Task form ko Django backend se connect karna baaki hai."
            );
        });
    }

    // View all tasks
    const viewAllBtn = document.getElementById("viewAllBtn");

    if (viewAllBtn) {
        viewAllBtn.addEventListener("click", function () {
            currentFilter = "all";
            currentSearch = "";

            if (globalSearch) {
                globalSearch.value = "";
            }

            filterButtons.forEach(function (button) {
                button.classList.toggle(
                    "active",
                    button.dataset.filter === "all"
                );
            });

            filterTasks();
        });
    }

});
```
