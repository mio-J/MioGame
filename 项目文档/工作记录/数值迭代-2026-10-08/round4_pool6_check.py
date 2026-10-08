"""Six designed town cards: exhaustive masks and reward histories, not engine QA."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
catalog = json.loads((HERE/'round3_card_results.json').read_text(encoding='utf-8'))['economic_cards']
catalog['警钟'] = {'unlock_town_level': 2, 'max_rank': 1}
names = list(catalog)

def check(active):
    counts = {str(n): [] for n in range(2, 7)}
    failures = []; leaves = 0; states = 0
    def visit(level, owned, history):
        nonlocal leaves, states
        if level == 7:
            leaves += 1
            return
        states += 1
        eligible = [n for n in active if catalog[n]['unlock_town_level'] <= level and owned.get(n, 0) < catalog[n]['max_rank']]
        counts[str(level)].append(len(eligible))
        if len(eligible) < 2:
            failures.append({'town_level': level, 'history': history, 'eligible': eligible})
        for choice in eligible:
            nxt = dict(owned); nxt[choice] = nxt.get(choice, 0) + 1
            visit(level + 1, nxt, history + [choice])
    visit(2, {}, [])
    return {'implemented_cards': active, 'release_pool_valid': not failures,
            'states': states, 'full_histories': leaves,
            'minimum_distinct_by_level': {k: min(v) if v else None for k, v in counts.items()},
            'first_failure': failures[0] if failures else None}

def main():
    results = [check([n for i, n in enumerate(names) if mask & (1 << i)]) for mask in range(64)]
    valid = [r for r in results if r['release_pool_valid']]
    assert len(valid) == 1 and valid[0]['implemented_cards'] == names
    assert list(valid[0]['minimum_distinct_by_level'].values()) == [4, 5, 4, 3, 2]
    without_alarm = next(r for r in results if r['implemented_cards'] == names[:-1])
    assert without_alarm['minimum_distinct_by_level']['6'] == 1
    result = {'actual_game_implementation_mask_verified': False,
              'checked_masks': 64, 'valid_masks': 1, 'catalog': catalog,
              'full_pool': valid[0], 'without_alarm': without_alarm, 'results': results,
              'limitations': 'All dependencies assumed implemented and unlocked as configured; actual runtime, save loading, effect functionality and further exclusions require separate QA.'}
    (HERE/'round4_pool6_results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ['checked_masks', 'valid_masks', 'full_pool']}, ensure_ascii=False))

if __name__ == '__main__':
    main()
