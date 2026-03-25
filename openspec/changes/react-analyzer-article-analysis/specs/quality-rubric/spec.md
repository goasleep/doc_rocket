## Overview

质量评分标准管理系统，支持多维度评分配置和版本管理。

## Requirements

### Functional Requirements

#### REQ-001: 评分维度
评分标准必须包含 4 个维度：
1. **content_depth** (权重 0.30): 内容深度与信息密度
2. **readability** (权重 0.25): 可读性与表达流畅度
3. **originality** (权重 0.25): 原创性与独特性
4. **virality_potential** (权重 0.20): 传播潜力与话题性

#### REQ-002: 评分档位
每个维度必须定义 5 个评分档位：
- 90-100: 优秀
- 80-89: 良好
- 70-79: 合格
- 60-69: 待改进
- 0-59: 不合格

每个档位必须有明确的文字描述。

#### REQ-003: 版本管理
- 支持创建多个评分标准版本
- 系统只维护一个 is_active=true 的标准
- 切换 active 标准时，新分析使用新标准，旧数据保留

#### REQ-004: API
- `GET /rubrics`: 列表评分标准
- `GET /rubrics/active`: 获取当前激活的标准
- `POST /rubrics`: 创建新标准
- `PATCH /rubrics/{id}`: 更新标准
- `POST /rubrics/{id}/activate`: 激活指定版本

### Data Model

```python
class RubricCriterion(BaseModel):
    min_score: int
    max_score: int
    description: str

class RubricDimension(BaseModel):
    name: str
    description: str
    weight: float
    criteria: list[RubricCriterion]

class QualityRubric(Document):
    id: UUID
    version: str
    name: str
    dimensions: list[RubricDimension]
    is_active: bool
    created_at: datetime
```

## Default Rubric (v1)

### content_depth
- **90-100**: 深度洞察，独家观点，数据支撑充分，有专业见解
- **80-89**: 内容充实，观点清晰，有一定数据/案例支撑
- **70-79**: 内容完整，观点明确，但缺乏深度挖掘
- **60-69**: 内容浅显，观点普通，信息密度低
- **0-59**: 内容空洞，缺乏实质信息

### readability
- **90-100**: 结构清晰，语言精炼，阅读体验极佳
- **80-89**: 结构合理，表达流畅，易于理解
- **70-79**: 结构基本清晰，偶有表达不畅
- **60-69**: 结构混乱，阅读有困难
- **0-59**: 难以理解，表达糟糕

### originality
- **90-100**: 独特视角，原创研究，行业首发
- **80-89**: 观点新颖，有独立思考，非简单整合
- **70-79**: 有一定个人见解，但参考痕迹明显
- **60-69**: 主要是信息整合，缺乏原创
- **0-59**: 大量抄袭或简单搬运

### virality_potential
- **90-100**: 热点话题，情绪共鸣强，极易传播
- **80-89**: 话题性强，有分享价值
- **70-79**: 有一定话题性，传播潜力一般
- **60-69**: 话题性弱，传播潜力低
- **0-59**: 无传播价值
