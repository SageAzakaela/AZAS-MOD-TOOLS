from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional
from uuid import uuid4

from ..config import settings


@dataclass
class Voice:
    id: str
    name: str
    color: str = "#FFFFFF"
    notes: str = ""
    groups: List[str] = field(default_factory=list)
    channel_hint: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class Character:
    id: str
    name: str
    notes: str = ""
    voice_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class Group:
    id: str
    name: str
    description: str = ""
    character_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class Line:
    text: str
    voice_id: Optional[str] = None
    duration: Optional[float] = None
    moodle: Optional[str] = None
    effects: List[str] = field(default_factory=list)
    sound_file: Optional[str] = None
    character_id: Optional[str] = None
    guid: str = field(default_factory=lambda: uuid4().hex)
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class Broadcast:
    id: str
    title: str
    description: str = ""
    lines: List[Line] = field(default_factory=list)
    start_offset: float = 0.0
    end_offset: Optional[float] = None
    adverts: List[str] = field(default_factory=list)
    effects: List[str] = field(default_factory=list)
    day: int = 0
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class Channel:
    id: str
    name: str
    frequency: float
    category: str = "radio"
    schedule: List["ChannelScheduleEntry"] = field(default_factory=list)
    auto_adverts: bool = False
    default_advert_group: str = ""
    start_script: str = "main"


@dataclass
class AdvertBroadcast:
    id: str
    timestamp: float = 0.0
    endstamp: float = 0.0
    day: int = 0
    advert_cat: str = "none"
    is_segment: bool = False
    lines: List[Line] = field(default_factory=list)


@dataclass
class AdvertScript:
    id: str
    name: str
    startdelay: float = 0.0
    timestampmode: str = "Static"
    loopmin: int = 1
    loopmax: int = 1
    lines: List[Line] = field(default_factory=list)
    broadcasts: List[AdvertBroadcast] = field(default_factory=list)


@dataclass
class VHSTape:
    id: str
    name: str
    description: str = ""
    broadcast_ids: List[str] = field(default_factory=list)
    spawn_weight: float = 1.0
    guid: str = field(default_factory=lambda: uuid4().hex)


@dataclass
class ChannelScheduleEntry:
    broadcast_id: str
    day: int
    start: float
    end: float

@dataclass
class CDCompilation:
    id: str
    name: str
    curator: str = ""
    track_ids: List[str] = field(default_factory=list)
    genre: str = "ambient"
    guid: str = field(default_factory=lambda: uuid4().hex)


@dataclass
class RecordedMediaLine:
    text: str
    r: float
    g: float
    b: float
    codes: Optional[str] = None
    guid: str = field(default_factory=lambda: uuid4().hex)


@dataclass
class RecordedMediaEntry:
    id: str
    title: str
    author: str
    category: str
    lines: List[RecordedMediaLine] = field(default_factory=list)
    spawn: int = 0
    extra: Optional[str] = None


@dataclass
class Project:
    voices: Dict[str, Voice] = field(default_factory=dict)
    broadcasts: Dict[str, Broadcast] = field(default_factory=dict)
    channels: Dict[str, Channel] = field(default_factory=dict)
    characters: Dict[str, Character] = field(default_factory=dict)
    groups: Dict[str, Group] = field(default_factory=dict)
    vhs_tapes: Dict[str, "VHSTape"] = field(default_factory=dict)
    cds: Dict[str, "CDCompilation"] = field(default_factory=dict)
    recorded_media: Dict[str, RecordedMediaEntry] = field(default_factory=dict)
    advertisements: Dict[str, AdvertScript] = field(default_factory=dict)

    def ensure_sample_data(self) -> None:
        return

    def create_broadcast(self, title: str, description: str = "") -> Broadcast:
        base = "".join(c.lower() if c.isalnum() else "_" for c in title) or "broadcast"
        candidate = base
        idx = 1
        while candidate in self.broadcasts:
            idx += 1
            candidate = f"{base}_{idx}"
        broadcast = Broadcast(id=candidate, title=title, description=description)
        self.broadcasts[broadcast.id] = broadcast
        return broadcast


@dataclass
class AppContext:
    project: Project = field(default_factory=Project)
    active_channel_id: Optional[str] = None
    active_broadcast_id: Optional[str] = None
    active_vhs_id: Optional[str] = None
    active_cd_id: Optional[str] = None
    _refresh_callbacks: List[Callable[[], None]] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        self.project.ensure_sample_data()
        self.active_channel_id = self.active_channel_id or next(iter(self.project.channels), None)
        self.active_broadcast_id = self.active_broadcast_id or next(iter(self.project.broadcasts), None)
        self.active_vhs_id = self.active_vhs_id or next(iter(self.project.vhs_tapes), None)
        self.active_cd_id = self.active_cd_id or next(iter(self.project.cds), None)

        if settings.auto_load_vanilla:
            from ..io import importers

            radio_path = settings.radio_data_path
            if radio_path.exists():
                importers.import_radio_data(self, str(radio_path))
                self.notify_data_changed()
            recorded_path = settings.recorded_media_path
            if recorded_path.exists():
                translation = settings.translation_path if settings.translation_path.exists() else None
                importers.import_recorded_media(
                    self, str(recorded_path), str(translation) if translation else None
                )
                self.notify_data_changed()

    @property
    def active_broadcast(self) -> Optional[Broadcast]:
        if self.active_broadcast_id:
            return self.project.broadcasts.get(self.active_broadcast_id)
        return None

    def select_broadcast(self, broadcast_id: str) -> None:
        if broadcast_id in self.project.broadcasts:
            self.active_broadcast_id = broadcast_id

    def add_broadcast(self, title: str, description: str = "") -> Broadcast:
        broadcast = self.project.create_broadcast(title, description)
        if self.active_channel_id:
            channel = self.project.channels.get(self.active_channel_id)
            if channel and broadcast.id not in channel.schedule:
                channel.schedule.append(
                    ChannelScheduleEntry(broadcast_id=broadcast.id, day=0, start=broadcast.start_offset, end=broadcast.end_offset or 0.0)
                )
        self.active_broadcast_id = broadcast.id
        return broadcast

    @property
    def active_vhs(self) -> Optional[VHSTape]:
        if self.active_vhs_id:
            return self.project.vhs_tapes.get(self.active_vhs_id)
        return None

    def select_vhs(self, tape_id: str) -> None:
        if tape_id in self.project.vhs_tapes:
            self.active_vhs_id = tape_id

    def add_vhs(self, name: str, description: str = "", spawn_weight: float = 1.0) -> VHSTape:
        tape_id = f"vhs-{len(self.project.vhs_tapes) + 1}"
        tape = VHSTape(id=tape_id, name=name, description=description, spawn_weight=spawn_weight)
        self.project.vhs_tapes[tape_id] = tape
        self.active_vhs_id = tape_id
        return tape

    @property
    def active_cd(self) -> Optional[CDCompilation]:
        if self.active_cd_id:
            return self.project.cds.get(self.active_cd_id)
        return None

    def select_cd(self, cd_id: str) -> None:
        if cd_id in self.project.cds:
            self.active_cd_id = cd_id

    def register_refresh_callback(self, callback: Callable[[], None]) -> None:
        self._refresh_callbacks.append(callback)

    def notify_data_changed(self) -> None:
        for callback in self._refresh_callbacks:
            try:
                callback()
            except Exception:
                pass

    def add_cd(self, name: str, curator: str = "", genre: str = "ambient") -> CDCompilation:
        cd_id = f"cd-{len(self.project.cds) + 1}"
        cd = CDCompilation(id=cd_id, name=name, curator=curator, genre=genre)
        self.project.cds[cd_id] = cd
        self.active_cd_id = cd_id
        return cd
