// Close flash messages
document.addEventListener('DOMContentLoaded', function () {
    // Close flash messages
    const closeButtons = document.querySelectorAll('.close-flash');
    closeButtons.forEach(button => {
        button.addEventListener('click', function () {
            this.parentElement.style.display = 'none';
        });
    });

    // Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.transition = 'opacity 0.3s';
            message.style.opacity = '0';
            setTimeout(() => {
                message.style.display = 'none';
            }, 300);
        }, 5000);
    });

    // Mobile menu toggle (if needed in future)
    const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
    const navMenu = document.querySelector('.nav-menu');

    if (mobileMenuToggle && navMenu) {
        mobileMenuToggle.addEventListener('click', function () {
            navMenu.classList.toggle('active');
        });
    }


    // AI summarize article
    const summaryButton = document.getElementById('btn-generate-summary');
    if (summaryButton) {
        summaryButton.addEventListener('click', function (e) {
            e.preventDefault();
            const url = summaryButton.dataset.url;
            if (!url) return;
            summaryButton.disabled = true;
            summaryButton.textContent = 'Đang tóm tắt...';
            fetch(url, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
                .then(res => res.json())
                .then(data => {
                    if (!data.ok) {
                        alert(data.error || 'Không thể tóm tắt bài viết.');
                        return;
                    }
                    const section = document.createElement('section');
                    section.className = 'article-summary';
                    section.innerHTML = '<h2>Tóm tắt nhanh</h2><p>' + data.summary + '</p>';
                    summaryButton.parentElement.replaceWith(section);
                })
                .catch(() => {
                    alert('Không thể tóm tắt bài viết.');
                });
        });
    }

    // Clear AI summary
    const clearSummaryButton = document.getElementById('btn-clear-summary');
    if (clearSummaryButton) {
        clearSummaryButton.addEventListener('click', function (e) {
            e.preventDefault();
            if (!confirm('Bạn có chắc chắn muốn xoá bản tóm tắt này không?')) return;

            const url = clearSummaryButton.dataset.url;
            fetch(url, {
                method: 'POST',
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
                .then(res => res.json())
                .then(data => {
                    if (data.ok) {
                        location.reload();
                    } else {
                        alert(data.error || 'Không thể xoá tóm tắt.');
                    }
                })
                .catch(() => alert('Lỗi kết nối.'));
        });
    }
});
