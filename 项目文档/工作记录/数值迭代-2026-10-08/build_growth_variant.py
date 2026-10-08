"""Build isolated S02-G; validate composition and clocks, not combat success."""
import copy
import json
from pathlib import Path
from normal_clock import normal_spawn_times

HERE = Path(__file__).resolve().parent
base = json.loads((HERE / 'survival_config.json').read_text(encoding='utf-8'))
variant = copy.deepcopy(base)
variant['config_id'] = 'S02-G'
variant['status'] = 'isolated_experiment_not_default_not_passed'
variant['base_config'] = 'survival_config.json'
variant['stages'][3].insert(3, {'iron':4, 'archer':4, 'green':8})
variant.pop('s02_clock')
variant['s02_stage_clocks'] = [[60,150,240,310] for _ in range(6)]
variant['s02_stage_clocks'][3] = [60,150,240,390,550]
variant['stage4_extra_spawn_batches'] = [
    {'relative_second':0,'composition':{'iron':4,'green':8}},
    {'relative_second':4,'composition':{'archer':4}},
]
variant['limitations'] = [
    '仅验证威胁预算与名义时钟，未验证阵容生产前置、战损、地图与经验',
    '清场时长沿用旧预测；新增小波及延长普通投放必须另行模拟',
    '经济3640秒延长候选不是新增压力已计入的完整通关账',
]
clear = [110,120,165,175,185,210]
def clock_summary(config, stage_clocks):
    start = config['initial_prepare']; events=[]; budget_count=0; ordinary=[]
    for idx, (stage, times) in enumerate(zip(config['stages'], stage_clocks)):
        assert len(stage) == len(times)
        assert 2 <= len(stage) - 1 <= 4
        assert all(a < b for a,b in zip(times,times[1:]))
        ordinary.append({'stage':idx+1,'root_budget_each':min(idx+1,4),
                         'local_spawn_seconds':normal_spawn_times(times),
                         'nominal_spawn_seconds':[start+t for t in normal_spawn_times(times)]})
        for n, composition in enumerate(stage):
            points = sum(config['threat_points'][k]*v for k,v in composition.items())
            assert points > 0
            budget_count += 1
            events.append({'stage':idx+1,'kind':'big' if n == len(stage)-1 else 'small',
                           'local_second':times[n],'nominal_second':start+times[n],
                           'budget':points,'composition':composition})
        start += times[-1]+clear[idx]+(config['rest'] if idx < 5 else 0)
    return {'events':events,'ordinary_spawn_log':ordinary,
            'predicted_end_seconds':start,'checked_wave_count':budget_count}

baseline = clock_summary(base,[base['s02_clock']]*6)
growth = clock_summary(variant,variant['s02_stage_clocks'])
assert baseline['predicted_end_seconds'] == 3395
assert growth['predicted_end_seconds'] == 3635
assert growth['checked_wave_count'] == 25
extra = [e for e in growth['events'] if e['stage']==4 and e['local_second']==390]
assert extra[0]['budget'] == 32
assert len(growth['ordinary_spawn_log'][3]['local_spawn_seconds']) == 11
assert sum(base['threat_points'][k]*v for k,v in {'iron':2,'archer':2,'green':4}.items()) == 16
for src in ('stages','s02_clock','rest','normal_interval'):
    assert base[src] == json.loads((HERE/'survival_config.json').read_text(encoding='utf-8'))[src]
for name, data in (('survival_growth_candidate.json',variant),
                   ('growth_variant_results.json',{'status':'budget_and_clock_checks_passed_only',
                                                   'baseline':baseline,'growth':growth})):
    (HERE/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'baseline_end':3395,'growth_end':3635,'growth_waves':25,'extra_budget':32},ensure_ascii=False))
