from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[2]/'设计文档'
points={'普通绿皮':'1','绿皮弓手':'2','孢囊怪':'孢囊3、孢巢7（含全谱系）','攀墙鬼':'3','投矛绿皮':'3','破咒小子':'4','铁皮绿皮':'4','野猪骑手':'5','巨怪':'18'}
for name,pt in points.items():
    p=ROOT/'敌人'/f'{name}.md';s=p.read_text(encoding='utf-8-sig')
    s=re.sub(r'<!-- enemy-baseline-20261008:start -->.*?<!-- enemy-baseline-20261008:end -->\s*','',s,flags=re.S)
    s+=f'''\n<!-- enemy-baseline-20261008:start -->
## 第二轮原型预算与结算（2026-10-08）

本轮威胁点 **{pt}**；根谱系本人击杀10XP/点、15米内友方击杀5XP/点；分裂子代不重复送XP/老兵星数/预算，但金币仍按原个体规则。基础HP、甲、单次攻击与速度沿本页，不以普遍涨生命制造难度。出场构成和时间唯一见[生存数值配置](../系统/生存数值配置.md)。

推进目标统一最近合法建筑，遇局部单位/墙按行为规则交战；不是无限直奔主城。特殊本体能力（魔免、越墙、五投矛、分裂、快慢差异）保留。大波及根谱系子代/生成队列清零才开始休整，母体死亡不提前清场。

| 版本 | 日期 | 变更 |
|---|---|---|
| 2026.10.08-B2 | 2026-10-08 | 统一威胁点、成长与谱系清场；原型需试玩 |
<!-- enemy-baseline-20261008:end -->
'''
    p.write_text(s,encoding='utf-8')
print('updated nine enemy docs')
