
SELECTORS = {
    "login": {
        "username": "input#username, input[name='username'], input[type='text']",
        "password": "input#password, input[name='password'], input[type='password']",
        "captcha_img": "img.captcha-image, img[src*='captcha'], .captcha img",
        "captcha_instruction": "div.captcha-instruction, .captcha-tip, .captcha-text",
        "submit": "button[type=submit], .login-btn, .login-submit, .submit-btn, button.el-button",
        "login_success_marker": "a.logout, .user-menu, .user-info, .avatar, .profile, .user-name, .user-avatar, .user-profile",
    },
    "courses": {
        "list_container": "div.course-list, .course-container, .list-container, .data-list",
        "item": "div.course-item, .course-row, .list-item, .data-row",
        "title": ".course-title, .title, .name, .course-name",
        "teacher": ".teacher-name, .teacher, .instructor, .author",
        "code": ".course-code, .code, .id, .course-id",
        "link": "a.course-detail, a[href*='course'], .link a",
        "next_button": "button.next, a.next, .pagination .next, .next-page",
        "empty_marker": ".no-data, .empty, .no-result, .empty-state",
    },
    "page_loading": {
        "loading_indicator": ".loading, .spinner, .loading-text, [class*='loading']",
        "content_ready": ".content, .main-content, .page-content, [class*='content']"
    },
    "workbench": {
        "user_info": ".user-info, .user-menu, .user-profile, .user-avatar, .avatar, .profile, .user-name, .user-account",
        "navigation": ".nav-menu, .sidebar, .menu, .navigation, .header, .top-bar, .toolbar",
        "main_content": ".workbench, .dashboard, .main-content, .content-area, .welcome, .greeting"
    }
}
