# Xiuxian whole-branch review fix report

日期：2026-09-02

## 修复

- 无战斗且存活时，层末触发 `meditation`，气血不超过上限。
- 使用 `trib` 死物时，`trib_run` 累计上限为 20。
- 天劫层 `info` 与 `inscribe` 一致显示硬渡、护体、心魔问道成功率。
- `giveup` 追加自绝记录前，先为上一层待补记录生成机械 `after`。
- 轮回境界从死亡时 `run.realm` 开始，只按折损后经验向下降境，不会升境。
- 为以上五项各增加一条聚焦回归测试，并修正旧轮回测试的死亡境界夹具。

## 命令与输出

### RED：新增五项回归测试

```text
cd skills/xiuxian
python3 -m unittest \
  tests.test_engine.TestChooseGrant.test_meditation_heals_after_non_battle_floor_and_clamps \
  tests.test_engine.TestFightUse.test_trib_item_caps_run_bonus_at_twenty \
  tests.test_engine.TestInscribe.test_tribulation_info_repeats_each_strategy_chance \
  tests.test_engine.TestChronicle.test_giveup_fills_previous_pending_after_before_appending \
  tests.test_engine.TestRebirth.test_preview_never_promotes_above_death_realm -v

Ran 5 tests in 0.152s
FAILED (failures=5)
```

五项分别得到预期失败：气血仍为 19、`trib_run` 为 30、`info` 成功率为空、上一层 `after` 为 `None`、筑基死亡后被错误提升为元婴。

### GREEN：五项聚焦测试

```text
cd skills/xiuxian
python3 -m unittest \
  tests.test_engine.TestChooseGrant.test_meditation_heals_after_non_battle_floor_and_clamps \
  tests.test_engine.TestFightUse.test_trib_item_caps_run_bonus_at_twenty \
  tests.test_engine.TestInscribe.test_tribulation_info_repeats_each_strategy_chance \
  tests.test_engine.TestChronicle.test_giveup_fills_previous_pending_after_before_appending \
  tests.test_engine.TestRebirth.test_preview_never_promotes_above_death_realm -v

Ran 5 tests in 0.063s
OK
```

### 完整测试

```text
cd skills/xiuxian
python3 -m unittest tests.test_engine -v

Ran 77 tests in 0.779s
OK
```

编辑器诊断：

```text
No linter errors found.
```
