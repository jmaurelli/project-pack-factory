# ai_native_package API

The template exports a small reusable surface:

- `build_agent_memory(memory_id, project_root, summary, memory_type, ...)` builds restart-state memory with structured goal, environment, and history inputs.
- `write_agent_memory(payload, output_path, replace_existing=False)` fails closed on duplicate `memory_id` unless replacement is explicit.
- `derive_agent_memory_path(memory_id, project_root)`
- `load_agent_memory(path)`
- `discover_agent_memory_paths(project_root, task_name=None)`
- `read_agent_memory(project_root, task_name=None, limit=7)` returns `restart_state` and `handoff_summary` for agent restarts.
- `build_agent_memory_snapshot(project_root, task_name=None, limit=7)` is the same reader surface for callers that want a snapshot helper.
- `run_agent_memory_benchmark(fixture_root=None, output_path=None, snapshot_output_path=None)` scores deterministic restart-state retrieval against an agent-oriented fixture.
- `get_package_metadata()`
- `get_output_metadata()`
- `format_output_metadata_markdown()`
- `build_output_attachment()`
- `build_path_payload(path_key, path_value)`
- `validate_task_goal(task_record_path, schema_path=None)`
- `run_task_goal_loop(task_record_path, schema_path=None, telemetry_output_path=None, run_id=None, build_run_manifest_path=None)`
- `discover_task_goal_telemetry_paths(project_root, task_name=None)`
- `load_task_goal_telemetry(path)`
- `load_task_goal_telemetry_summary(project_root)`
- `discover_build_run_manifest_paths(project_root)`
- `load_build_run_manifest(path)`
- `read_agent_telemetry(project_root, task_name=None)`
- `build_agent_telemetry_snapshot(project_root, task_name=None)`
- `derive_task_goal_telemetry_path(task_name, project_root)`
- `write_task_goal_telemetry(payload, output_path)`
- `build_task_goal_telemetry_summary(telemetry_paths, generated_at=None)`
- `derive_task_goal_telemetry_summary_path(project_root)`
- `write_task_goal_telemetry_summary(payload, output_path)`

Future packages can extend the API, but should keep the scaffold exports deterministic and package-root local.
