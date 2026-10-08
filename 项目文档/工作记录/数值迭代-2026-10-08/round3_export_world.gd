extends SceneTree
## Read-only export of actual generated world; no gameplay or unit navigation test.
func _initialize() -> void:
	call_deferred("export_world")

func export_world() -> void:
	var cfg := WorldConfig.new()
	cfg.world_seed = 20260918
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
	var result := {"seed": cfg.world_seed, "world_tiles": cfg.world_tiles,
		"grid_size": data.size, "cell_m": cell, "spawn": [spawn.x, spawn.z],
		"walkable_base64": Marshalls.raw_to_base64(grid), "deposits": deposits,
		"method": "actual_world_generator_plus_candidate_grid_navigation",
		"grid_rule": "smooth_slope_tan<=0.6 and sampled_water_depth<=0.15m; no unit collision or structures",
		"navigation_is_gameplay_measured": false}
	var output := "C:/Users/26915/OneDrive/文档/异星开拓史/MioGame/项目文档/工作记录/数值迭代-2026-10-08/round3_world_seed.json"
	var file := FileAccess.open(output, FileAccess.WRITE)
	if file == null:
		push_error("Cannot write world audit output")
		quit(1)
		return
	file.store_string(JSON.stringify(result))
	file.close()
	print("WORLD_AUDIT_EXPORTED seed=", cfg.world_seed, " deposits=", deposits.size())
	quit()
