from __future__ import annotations

HERO_NAMES = {
    "steel_guardian": "钢铁守护者",
    "temple_warden": "圣殿守卫",
    "thorn_brute": "荆棘暴徒",
    "berserker": "狂战士",
    "shadow_blade": "影刃",
    "halberd_commander": "戟卫统领",
    "hunter_ranger": "猎风游侠",
    "repeater_engineer": "连弩工匠",
    "demolitionist": "爆破专家",
    "arcane_scholar": "奥术学者",
    "frost_witch": "霜巫",
    "void_hexer": "虚咒术师",
    "sacred_priest": "圣职祭司",
    "war_song_bard": "战歌诗人",
    "chrono_sage": "时序贤者",
}

SKILL_NAMES = {
    "shield_strike": "盾击",
    "fortress_stand": "堡垒坚守",
    "armor_reverb": "护甲回响",
    "holy_hammer": "圣锤",
    "sacred_shelter": "神圣庇护",
    "loyal_intercept": "忠诚拦截",
    "thorn_fist": "棘拳",
    "thorn_tide": "荆潮",
    "bloodbone_rage": "血骨狂怒",
    "rending_slash": "裂伤斩",
    "blood_combo": "狂血连斩",
    "murder_fervor": "杀意沸腾",
    "shadow_assault": "影袭",
    "night_execution": "夜幕处决",
    "dusk_steps": "暮步",
    "halberd_thrust": "戟刺",
    "formation_breaker": "破阵",
    "command_pressure": "统御压迫",
    "piercing_arrow": "穿刺箭",
    "arrow_storm": "箭雨",
    "precise_hunt": "精准猎杀",
    "double_bolt": "双重弩击",
    "overdrive_barrage": "过载齐射",
    "clockwork_overload": "发条过载",
    "firebomb": "火焰炸弹",
    "blast_volley": "爆裂齐射",
    "powder_festival": "火药狂欢",
    "arcane_bolt": "奥术飞弹",
    "meteor_rite": "陨星仪式",
    "elemental_resonance": "元素共鸣",
    "frost_spike": "寒冰尖刺",
    "glacial_tempest": "冰川风暴",
    "cold_domain": "寒域",
    "void_mark": "虚空印记",
    "abyss_curse": "深渊诅咒",
    "curse_echo": "咒蚀回声",
    "holy_wave": "圣光波",
    "grace_prayer": "恩典祈祷",
    "afterglow_blessing": "余辉祝福",
    "rally_chord": "集结和弦",
    "victory_anthem": "凯歌",
    "echo_of_encouragement": "激励回响",
    "time_pulse": "时间脉冲",
    "timeline_sync": "时间线同步",
    "foresight_loop": "先见循环",
}

ROLE_NAMES = {
    "tank": "坦克",
    "melee_dps": "近战输出",
    "ranged_dps": "远程输出",
    "mage": "法师",
    "support": "辅助",
}

POSITION_NAMES = {
    "frontline": "前排",
    "backline": "后排",
}

RARITY_NAMES = {
    "magic": "魔法",
    "rare": "稀有",
    "legendary": "传奇",
}

SLOT_NAMES = {
    "weapon": "武器",
    "helmet": "头盔",
    "chest": "胸甲",
    "gloves": "护手",
    "pants": "腿甲",
    "boots": "战靴",
    "amulet": "护符",
    "ring": "戒指",
}

SPECIALIZATION_NAMES = {
    "none": "未选择",
    "bulwark": "壁垒",
    "sentinel": "守望",
    "slayer": "屠戮",
    "duelist": "决斗",
    "deadeye": "神射",
    "barrage": "连射",
    "spellweaver": "织法",
    "frostbound": "霜缚",
    "oracle": "神谕",
    "chorister": "咏唱",
}

STATUS_NAMES = {
    "taunt": "嘲讽",
    "haste": "急速",
    "slow": "减速",
    "stun": "眩晕",
    "freeze": "冰冻",
    "burn": "灼烧",
    "bleed": "流血",
    "erosion": "腐蚀",
    "weaken": "虚弱",
}

THREAT_TAG_NAMES = {
    "control": "控制",
    "high_burst": "高爆发",
    "sustain": "续航",
    "frontline_wall": "前排壁垒",
    "elite_spike": "精英尖峰",
    "boss_pressure": "首领压制",
    "backline_pressure": "后排威胁",
    "aoe_pressure": "范围压制",
    "tempo_support": "节奏支援",
}

ENCOUNTER_TYPE_NAMES = {
    "normal": "普通",
    "elite": "精英",
    "boss": "首领",
}

WINNER_NAMES = {
    "ally": "我方",
    "enemy": "敌方",
}

PARTY_STATUS_NAMES = {
    "party": "上阵",
    "bench": "待命",
}

VERDICT_NAMES = {
    "upgrade": "升级",
    "sidegrade": "平替",
}

THEME_NAMES = {
    "Frozen Court": "霜封王庭",
    "Chrono Dragon Siege": "时龙围城",
    "Bulwark Phalanx": "壁垒方阵",
    "Infernal Bombardment": "炼狱轰击",
    "Assassin Volley": "刺客齐射",
}

ENCOUNTER_NAMES = {
    "Iron Wall Patrol": "铁壁巡逻队",
    "Night Ambush Cell": "夜袭伏击组",
    "Frostwitch Honor Guard": "霜巫荣誉卫队",
    "Demolition Battery": "爆破火力组",
    "Chrono Sage Ascendant": "升格时序贤者",
}

ASPECT_NAMES = {
    "embers_feed_energy": "余烬回能",
    "barrier_haste": "屏障疾行",
    "predator_fury": "猎杀狂热",
    "saints_resolve": "圣誓决心",
}

ASPECT_DESCRIPTIONS = {
    "embers_feed_energy": "攻击带有减益的目标时，回复 5 点能量。",
    "barrier_haste": "自身有护盾时攻击，会额外推进 60 点行动条。",
    "predator_fury": "攻击生命低于一半的目标时，回复 4 点能量。",
    "saints_resolve": "治疗生命低于一半的目标后，为其附加相当于治疗量 35% 的护盾。",
}

AFFIX_NAMES = {
    "hp_pct": "生命百分比",
    "atk_pct": "攻击百分比",
    "mag_pct": "法强百分比",
    "armor_flat": "护甲",
    "resist_flat": "抗性",
    "speed_flat": "速度",
    "crit_rate": "暴击率",
    "crit_damage": "暴击伤害",
    "energy_gain_bonus": "能量获取",
    "heal_bonus": "治疗加成",
    "shield_bonus": "护盾加成",
    "damage_vs_debuffed": "易伤增伤",
    "damage_bonus": "伤害加成",
}

ENGLISH_HERO_TO_ID = {
    "Steel Guardian": "steel_guardian",
    "Temple Warden": "temple_warden",
    "Thorn Brute": "thorn_brute",
    "Berserker": "berserker",
    "Shadow Blade": "shadow_blade",
    "Halberd Commander": "halberd_commander",
    "Hunter Ranger": "hunter_ranger",
    "Repeater Engineer": "repeater_engineer",
    "Demolitionist": "demolitionist",
    "Arcane Scholar": "arcane_scholar",
    "Frost Witch": "frost_witch",
    "Void Hexer": "void_hexer",
    "Sacred Priest": "sacred_priest",
    "War Song Bard": "war_song_bard",
    "Chrono Sage": "chrono_sage",
}

ENGLISH_SKILL_TO_ID = {
    "Shield Strike": "shield_strike",
    "Fortress Stand": "fortress_stand",
    "Armor Reverb": "armor_reverb",
    "Holy Hammer": "holy_hammer",
    "Sacred Shelter": "sacred_shelter",
    "Loyal Intercept": "loyal_intercept",
    "Thorn Fist": "thorn_fist",
    "Thorn Tide": "thorn_tide",
    "Bloodbone Rage": "bloodbone_rage",
    "Rending Slash": "rending_slash",
    "Blood Combo": "blood_combo",
    "Murder Fervor": "murder_fervor",
    "Shadow Assault": "shadow_assault",
    "Night Execution": "night_execution",
    "Dusk Steps": "dusk_steps",
    "Halberd Thrust": "halberd_thrust",
    "Formation Breaker": "formation_breaker",
    "Command Pressure": "command_pressure",
    "Piercing Arrow": "piercing_arrow",
    "Arrow Storm": "arrow_storm",
    "Precise Hunt": "precise_hunt",
    "Double Bolt": "double_bolt",
    "Overdrive Barrage": "overdrive_barrage",
    "Clockwork Overload": "clockwork_overload",
    "Firebomb": "firebomb",
    "Blast Volley": "blast_volley",
    "Powder Festival": "powder_festival",
    "Arcane Bolt": "arcane_bolt",
    "Meteor Rite": "meteor_rite",
    "Elemental Resonance": "elemental_resonance",
    "Frost Spike": "frost_spike",
    "Glacial Tempest": "glacial_tempest",
    "Cold Domain": "cold_domain",
    "Void Mark": "void_mark",
    "Abyss Curse": "abyss_curse",
    "Curse Echo": "curse_echo",
    "Holy Wave": "holy_wave",
    "Grace Prayer": "grace_prayer",
    "Afterglow Blessing": "afterglow_blessing",
    "Rally Chord": "rally_chord",
    "Victory Anthem": "victory_anthem",
    "Echo of Encouragement": "echo_of_encouragement",
    "Time Pulse": "time_pulse",
    "Timeline Sync": "timeline_sync",
    "Foresight Loop": "foresight_loop",
}

LOOT_NAME_REPLACEMENTS = [
    ("Saintsworn", "圣誓"),
    ("Stormforged", "风暴铸造"),
    ("Nightglass", "夜璃"),
    ("Emberwake", "烬醒"),
    ("Voidtouched", "虚触"),
    ("Mythic", "神话"),
    ("Kingshade", "王影"),
    ("Duskworn", "暮影"),
    ("Ironbound", "铁铸"),
    ("Mistlit", "雾辉"),
    ("Ashen", "灰烬"),
    ("Dragonwake", "龙醒"),
    ("Weapon", "武器"),
    ("Pike", "长枪"),
    ("Staff", "法杖"),
    ("Charm", "符坠"),
    ("Blade", "利刃"),
    ("Sword", "长剑"),
    ("Hammer", "战锤"),
    ("Bow", "长弓"),
    ("Orb", "法球"),
    ("Gun", "火枪"),
    ("Dagger", "匕首"),
    ("Mace", "钉锤"),
    ("Helm", "头盔"),
    ("Cuirass", "胸甲"),
    ("Grips", "护手"),
    ("Legguards", "腿甲"),
    ("Treads", "战靴"),
    ("Amulet", "护符"),
    ("Ring", "戒指"),
    (" of Embers", "·余烬"),
]


def hero_name(hero_id: str, fallback: str | None = None) -> str:
    return HERO_NAMES.get(hero_id, fallback or hero_id)


def hero_name_from_text(text: str) -> str:
    hero_id = ENGLISH_HERO_TO_ID.get(text)
    return hero_name(hero_id, text) if hero_id else text


def skill_name(skill_id: str, fallback: str | None = None) -> str:
    return SKILL_NAMES.get(skill_id, fallback or skill_id)


def skill_name_from_text(text: str) -> str:
    skill_id = ENGLISH_SKILL_TO_ID.get(text)
    return skill_name(skill_id, text) if skill_id else text


def role_name(role: str) -> str:
    return ROLE_NAMES.get(role, role)


def position_name(position: str) -> str:
    return POSITION_NAMES.get(position, position)


def rarity_name(rarity: str) -> str:
    return RARITY_NAMES.get(rarity, rarity)


def slot_name(slot: str) -> str:
    return SLOT_NAMES.get(slot, slot)


def specialization_name(specialization: str) -> str:
    return SPECIALIZATION_NAMES.get(specialization, specialization or "未选择")


def status_name(status_id: str) -> str:
    return STATUS_NAMES.get(status_id, status_id)


def threat_tag_name(tag: str) -> str:
    return THREAT_TAG_NAMES.get(tag, tag)


def encounter_type_name(encounter_type: str) -> str:
    return ENCOUNTER_TYPE_NAMES.get(encounter_type, encounter_type)


def winner_name(winner: str) -> str:
    return WINNER_NAMES.get(winner, winner)


def party_status_name(status: str) -> str:
    return PARTY_STATUS_NAMES.get(status, status)


def verdict_name(verdict: str) -> str:
    return VERDICT_NAMES.get(verdict, verdict)


def theme_name(theme: str) -> str:
    return THEME_NAMES.get(theme, theme)


def encounter_name(name: str) -> str:
    return ENCOUNTER_NAMES.get(name, name)


def aspect_name(aspect: str) -> str:
    return ASPECT_NAMES.get(aspect, aspect)



def aspect_description(aspect: str) -> str:
    return ASPECT_DESCRIPTIONS.get(aspect, "")



def affix_name(affix: str) -> str:
    return AFFIX_NAMES.get(affix, affix)


def localize_loot_name(name: str) -> str:
    localized = name
    for source, target in LOOT_NAME_REPLACEMENTS:
        localized = localized.replace(source, target)
    return localized
