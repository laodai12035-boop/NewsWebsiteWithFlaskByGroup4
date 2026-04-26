// Close flash messages
document.addEventListener('DOMContentLoaded', function() {
    // Close flash messages
    const closeButtons = document.querySelectorAll('.close-flash');
    closeButtons.forEach(button => {
        button.addEventListener('click', function() {
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
        mobileMenuToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });
    }

    // Inline image upload for article content
    const inlineImageInput = document.getElementById('inline_image_file');
    const contentTextarea = document.getElementById('content');

    function insertAtCursor(textarea, text) {
        if (!textarea) return;
        const start = textarea.selectionStart || 0;
        const end = textarea.selectionEnd || 0;
        const before = textarea.value.substring(0, start);
        const after = textarea.value.substring(end);
        textarea.value = before + text + after;
        const pos = start + text.length;
        textarea.selectionStart = textarea.selectionEnd = pos;
        textarea.focus();
    }

    if (inlineImageInput && contentTextarea) {
        inlineImageInput.addEventListener('change', function () {
            if (!inlineImageInput.files || inlineImageInput.files.length === 0) {
                return;
            }
            const file = inlineImageInput.files[0];
            const formData = new FormData();
            formData.append('file', file);

            inlineImageInput.disabled = true;

            fetch('/dashboard/uploads/images', {
                method: 'POST',
                body: formData
            })
                .then(res => res.json())
                .then(data => {
                    if (!data.ok) {
                        alert(data.error || 'Upload ảnh thất bại');
                        return;
                    }
                    const url = data.url;
                    const snippet = `\n\n<img src="${url}" alt="Ảnh minh họa">\n\n`;
                    insertAtCursor(contentTextarea, snippet);
                })
                .catch(() => {
                    alert('Không thể upload ảnh.');
                })
                .finally(() => {
                    inlineImageInput.value = '';
                    inlineImageInput.disabled = false;
                });
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
});
