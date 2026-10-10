"""Проверка установленной гибридной генерации, без записи в базу и без GigaChat."""
from app.reference import GRADE_LEVEL, SPEC_CODES
from app.services.testing_engine import build_items, score_attempt, public_item

SOLUTIONS = {
    'be.code.sum_positives': 'def solve(arr):\n    return sum(x for x in arr if x > 0)',
    'be.code.sequence_lookup': '''def solve(nums, target):
    left, right = 0, len(nums)-1
    while left <= right:
        mid = (left+right)//2
        if nums[mid] == target: return mid
        if nums[mid] < target: left = mid+1
        else: right = mid-1
    return -1''',
    'be.code.missing_number': 'def solve(arr):\n    n = len(arr)\n    return n*(n+1)//2-sum(arr)',
    'be.code.continuous_stream': '''def solve(arr, k):
    window = sum(arr[:k])
    best = window
    for i in range(k, len(arr)):
        window += arr[i]-arr[i-k]
        best = max(best, window)
    return best''',
    'be.code.first_unique': '''def solve(arr):
    counts = {}
    for x in arr: counts[x] = counts.get(x, 0)+1
    for x in arr:
        if counts[x] == 1: return x
    return -1''',
    'be.code.network_routing': '''from collections import deque
def solve(n, edges, start, target):
    graph = [[] for _ in range(n)]
    for a, b in edges:
        graph[a].append(b)
        graph[b].append(a)
    queue = deque([(start, 0)])
    seen = {start}
    while queue:
        node, distance = queue.popleft()
        if node == target: return distance
        for nxt in graph[node]:
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, distance+1))
    return -1''',
    'be.code.dp_max_profit': '''def solve(arr):
    prev, current = 0, 0
    for x in arr: prev, current = current, max(current, prev+x)
    return current''',
}

# Эталонные алгоритмы для проверки 48 шаблонов ML-команды.
CONTEST_SOLUTIONS = {
    'easy_sum': 'def solve(arr):\n    return sum(x for x in arr if x > 0)',
    'hard_diff': 'def solve(arr):\n    return max((abs(a-b) for a,b in zip(arr,arr[1:])), default=0)',
    'easy_lookup': SOLUTIONS['be.code.sequence_lookup'].replace('nums', 'arr'),
    'mid_missing': SOLUTIONS['be.code.missing_number'],
    'hard_anagram': 'def solve(s1,s2):\n    return int(sorted(s1) == sorted(s2))',
    'easy_unique': SOLUTIONS['be.code.first_unique'],
    'mid_stream': SOLUTIONS['be.code.continuous_stream'],
    'hard_intervals': """def solve(intervals):
    events = []
    for start,end in intervals:
        events.append((start,1))
        events.append((end,-1))
    current = best = 0
    for _, delta in sorted(events):
        current += delta
        best = max(best,current)
    return best""",
    'easy_dp': SOLUTIONS['be.code.dp_max_profit'],
    'mid_routing': SOLUTIONS['be.code.network_routing'],
    'hard_clusters': """def solve(n,edges):
    graph = [[] for _ in range(n)]
    for a,b in edges:
        graph[a].append(b)
        graph[b].append(a)
    seen = set()
    count = 0
    for node in range(n):
        if node in seen: continue
        count += 1
        stack = [node]
        seen.add(node)
        while stack:
            for nxt in graph[stack.pop()]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
    return count""",
}


def solution_for(item):
    id_ = item['template_id']
    if id_ in SOLUTIONS:
        return SOLUTIONS[id_]
    suffix = id_.split('.code.')[1].split('_',1)[1]
    if suffix == 'mid_count':
        counted = {'fe':404, 'ds':-1, 'qa':0, 'do':1, 'be':500}[id_.split('.')[0]]
        return f'def solve(arr):\n    return arr.count({counted})'
    return CONTEST_SOLUTIONS[suffix]

# Совместимость эталонных решений с существующими проверками API.
from app.testing_bank import templates_for
from app.services.testing_engine import template_difficulty
for _spec in SPEC_CODES:
    for _template in templates_for(_spec):
        if template_difficulty(_template):
            SOLUTIONS[_template.id] = solution_for({'template_id': _template.id})


def main():
    for spec in SPEC_CODES:
        for grade, level in GRADE_LEVEL.items():
            items = build_items(spec, grade, 20261010)
            assert len(items) == 3 and all(i['level'] == level for i in items)
            assert [i['base_weight'] + i['bonus_weight'] for i in items] == [20,30,50]
            assert [i['difficulty'] for i in items] == ['easy','medium','hard']
            assert len({i['template_id'] for i in items}) == 3
            result = score_attempt(items, {i['id']: solution_for(i) for i in items})
            assert result['score'] == 100, result
            assert all('tests' not in public_item(i)['code'] for i in items)
            print(f'{spec}/{grade}: 3 задачи, easy/medium/hard, 20/30/50, решения 100/100')
    print('OK: contest-scoring-all-5')


if __name__ == '__main__':
    main()
