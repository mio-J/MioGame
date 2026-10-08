extends SceneTree
## Read-only multi-seed export, derived from round3_export_world.gd (which is NOT run again, so its output is untouched).
## Run: godotc --headless --path <AlienFrontier> -s <this file>. Change outdir to any scratch folder first.
## The seed_*.json written by the 2026-10-08 run were gzipped into round5_seed_exports/ and are read by round5_multiseed_supply.py.
func _initialize() -> void:
	call_deferred("export_all")

func export_all() -> void:
	var seeds := [20260918, 11, 202, 3033, 40404, 5, 77777, 123456, 987654, 31415]
	var outdir := "C:/Users/26915/AppData/Local/Temp/claude/C--Users-26915-OneDrive---------/56edb889-8368-4991-9eb4-f48a9a0c4fc7/scratchpad/"
	for s in seeds:
		var cfg := WorldConfig.new()
		cfg.world_seed = s
		cfg.precompute_foliage = false
		var data := WorldGenerator.new(cfg).generate()
		var slopes := data.smooth_slope()
		var grid := PackedByteArray()
		var cell := float(cfg.world_tiles) / data.size
		grid.resize(data.size * data.size)
		for z in data.size:
			for x in data.size:
				var tx := (x + 0.5) * cell
				var tz := (z + 0.5) * cell
				var i := z * data.size + x
				grid[i] = 1 if slopes[i] <= 0.6 and data.water_depth_at_tile(tx, tz) <= 0.15 else 0
		var deposits: Array = []
		for dep in data.deposits:
			deposits.append(dep.to_dict())
		var spawn := data.spawn_world_position()
		var result := {"seed": s, "world_tiles": cfg.world_tiles,
			"grid_size": data.size, "cell_m": cell, "spawn": [spawn.x, spawn.z],
			"walkable_base64": Marshalls.raw_to_base64(grid), "deposits": deposits,
			"grid_rule": "smooth_slope_tan<=0.6 and sampled_water_depth<=0.15m; no unit collision or structures"}
		var f := FileAccess.open(outdir + "seed_%d.json" % s, FileAccess.WRITE)
		f.store_string(JSON.stringify(result))
		f.close()
		print("EXPORTED seed=", s, " deposits=", deposits.size())
	quit()
