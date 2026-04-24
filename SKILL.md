---
name: fortune-telling-bazi
description: 八字算命 skill — 支持多人八字存储+联合分析，首次询问生日，后续对话自动附带八字信息。说"停止算命"退出。
---

# fortune-telling-bazi 八字算命

## 核心流程

### 首次启用
1. 用户说「开始算命」→ 调用 `fortune.py status`
2. 无用户 → 询问生日（姓名/年份/月份/日期/时辰/性别）
3. 调用 `fortune.py add <name> <年> <月> <日> <时> <分> <性别>`
4. 接口返回八字 → 保存到 `data/users.json` → 显示摘要
5. 调用 `fortune.py active <name>` 激活
6. **标记 `is_active = true`**，此后每条回复注入八字摘要

### 非首次启用
1. 用户说「开始算命」→ `fortune.py status`
2. 有记录 → 显示所有已保存用户列表，询问「用哪个/哪几个」
3. 用户选一个或多个人 → `fortune.py active <name1,name2,...>`
4. 标记 `is_active = true`，注入对应八字摘要

### 退出
- 用户说「停止算命」→ `is_active = false`

---

## 数据文件

```
data/
├── users.json     # 所有用户的生日+八字
└── active.json    # 当前激活的用户列表
```

---

## 命令一览

| 命令 | 功能 |
|------|------|
| `fortune.py add <name> <year> <month> <day> <hour> <minute> <gender>` | 添加新用户 |
| `fortune.py update <name> <year> <month> <day> <hour> <minute> <gender>` | 更新已有用户 |
| `fortune.py list` | 列出所有已保存用户 |
| `fortune.py view [name]` | 查看某人八字详情（默认当前激活） |
| `fortune.py remove <name>` | 删除某人八字 |
| `fortune.py active [name1,name2,...]` | 设置激活用户，多人用逗号分隔 |
| `fortune.py status` | 检查激活状态 |
| `fortune.py joint [name1,name2]` | 联合分析（默认当前激活用户） |

---

## 八字摘要格式（单人被注入到 context）

```
━━━ 八字信息 ━━━
姓名：{name} | {gender} | 农历{lunar}
八字：{year_ganzhi} {month_ganzhi} {day_ganzhi} {hour_ganzhi}
五行：{wuxing} | {mingge} | {wangshuai}
喜用：{xiyong}
旺运：{current_dayun_year}（{dayun_ganzhi}）
神煞：{shensha}
━━━ 八字信息 ━━━
```

## 联合分析格式（多人被注入到 context）

```
━━━ 联合分析 ━━━
【{name1}】{gender} | {bazi_str} | {mingge}
【{name2}】{gender} | {bazi_str} | {mingge}
━━━ 合冲刑害 ━━━
年支关系：{analysis}
日支关系：{analysis}（夫妻/伴侣位）
月支关系：{analysis}
━━━ 五行契合 ━━━
{analysis}
━━━ 婚配分析 ━━━
{analysis}（仅两人时）
━━━ 八字信息 ━━━
```

---

## 触发关键词

| 关键词 | 动作 |
|--------|------|
| `开始算命`、`算命`、`看看八字`、`我的八字` | 激活算命流程 |
| `停止算命`、`不算了`、`退出算命` | 退出算命模式 |
| `联合分析`、`合盘`、`双人八字` | 触发联合分析 |
| `添加八字`、`加个人`、`录入八字` | 添加新用户 |
| `查看用户`、`都有谁`、`八字体检` | 列出所有已保存用户 |

---

## 联合分析内容

**地支关系分析：**
- 年支 vs 年支（双方祖辈/原生家庭/根基是否相合）
- 日支 vs 日支（夫妻/伴侣位合冲刑害）
- 月支 vs 月支（父母/环境/外环境关系）

**五行契合分析：**
- 喜用五行是否相生（你生我或我生你为吉）
- 五行是否互补

**婚配分析（仅两人时）：**
- 日支合冲刑害婚姻判断
- 桃花重叠警告
- 天乙贵人重叠吉兆

---

## 注意事项

- `fortune.py joint` 支持2-N人联合分析，默认用当前激活用户
- 激活多个用户时，所有人的摘要都注入 context
- 若只激活一人，格式同单人摘要
- 接口偶尔失败，重试一次即可
- 注入摘要时放在回复最前面，然后回答问题
