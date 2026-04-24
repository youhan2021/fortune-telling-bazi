---
name: fortune-telling-bazi
description: 八字算命 skill — 首次询问生日获取八字并保存，后续对话自动附带八字信息。停止说"停止算命"退出。
---

# fortune-telling 八字算命

## 核心机制

**首次启用流程：**
1. 用户说「开始算命」→ agent 调用 `fortune.py status`
2. 无记录 → 询问生日（年份/月份/日期/时辰/性别）
3. 用户提供生日 → 调用 `fortune.py fetch <年> <月> <日> <时> <分> <性别>`
4. 接口返回完整八字 → 保存到 `data/user.json` → 显示八字摘要
5. **标记 `is_active = true`**，此后每条回复在末尾注入八字摘要

**非首次启用流程：**
1. 用户说「开始算命」→ agent 调用 `fortune.py status`
2. 有记录 → 显示已保存的八字摘要
3. 询问「是否使用这个信息？输入新生日可更新，否则直接开始」
4. 用户说新生日 → `fortune.py fetch` 更新
5. 用户确认 → 标记 `is_active = true`

**退出机制：**
- 用户说「停止算命」→ `is_active = false` → agent 不再注入八字信息

---

## 激活状态管理

`saved_context` 中保存 `is_active` 标志：
- `is_active: true` → 每次回复前在 context 注入八字摘要
- `is_active: false` → 不注入

---

## 数据文件

```
data/
└── user.json     # 用户生日 + 八字原始数据 + fetched_at 时间戳
```

---

## 命令（agent 内部调用）

| 命令 | 功能 |
|------|------|
| `fortune.py status` | 检查是否已有保存的八字。有记录输出 `EXISTS:...`，无记录输出 `NOT_FOUND` |
| `fortune.py fetch <year> <month> <day> <hour> <minute> <gender>` | 调用接口获取八字，保存到 user.json |
| `fortune.py view` | 显示已保存八字的格式化摘要 |
| `fortune.py clear` | 删除 user.json（停止算命时调用） |

---

## 八字摘要格式（注入到 context）

每次回复前拼贴以下格式到 context：

```
━━━ 八字信息 ━━━
性别：{gender} | {lunar_date} {hour}时
八字：{year_ganzhi} {month_ganzhi} {day_ganzhi} {hour_ganzhi}
五行：{wuxing} | {mingge} | {wangshuai}
喜用：{xiyong}
旺运年份：{current_dayun_year}（{dayun_ganzhi}）
神煞：{shensha}
━━━ 八字信息 ━━━
```

---

## 触发关键词

| 关键词 | 动作 |
|--------|------|
| `开始算命`、`算命`、`看看八字`、`我的八字` | 激活算命流程 |
| `停止算命`、`不算了`、`退出算命` | 退出算命模式 |

---

## 注意事项

- 接口为 suanzhun.net，偶尔失败重试一次即可
- `fetch` 成功后才保存；失败打印错误，不保存脏数据
- 若用户未提供完整生日信息，列出格式模板请用户补充
- 注入八字摘要时放在回复最前面，然后再回答用户问题
- 停止算命后清除 `is_active` 标志，但保留 user.json（方便下次快速确认）
