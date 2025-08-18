```python
# 用户菜单选择器（按优先级排序）
user_menu_selector_1 = '[class*='user']'  #  (class: el-icon el-icon-user-solid font-size80 text-color-info margin-top-30)
user_menu_selector_2 = '.el-dropdown'  # 李嘉李 (class: el-dropdown)

# 个人信息菜单项选择器（按优先级排序）
personal_info_selector_1 = 'text=个人信息'  # 个人信息补填
personal_info_selector_2 = '.el-menu-item'  # 测评列表

# 操作流程
await page.goto(workbench_url)
await page.wait_for_load_state('domcontentloaded')
await page.locator(user_menu_selector_1).click()
await page.wait_for_timeout(1000)
await page.locator(personal_info_selector_1).click()
await page.wait_for_load_state('domcontentloaded')
```