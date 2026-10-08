"""Nominal ordinary spawns: small starts take precedence and pause 20 seconds."""
def normal_spawn_times(local_times, interval=40, hold_seconds=20):
    small = set(local_times[:-1]); elapsed=0; hold_until=0; times=[]
    for second in range(1,local_times[-1]):
        if second in small:
            hold_until=max(hold_until,second+hold_seconds)
        if second < hold_until:
            continue
        elapsed += 1
        if elapsed == interval:
            times.append(second); elapsed=0
    return times

if __name__ == '__main__':
    import json
    short = normal_spawn_times([60,140,220,280])
    standard = normal_spawn_times([60,150,240,310])
    growth = normal_spawn_times([60,150,240,390,550])
    assert short == [40,100,160,200,260]
    assert standard == [40,100,140,200,260,300]
    assert growth == [40,100,140,200,260,300,340,380,440,480,520]
    print(json.dumps({'S01':short,'S02':standard,'S02_G_stage4':growth}))
