from enum import Enum

from qfluentwidgets import QConfig, OptionsConfigItem, EnumSerializer, OptionsValidator


class MvQuality(Enum):
    """ MV quality enumeration class """

    FULL_HD = "Full HD"
    HD = "HD"
    SD = "SD"
    LD = "LD"

    @staticmethod
    def values():
        return [q.value for q in MvQuality]


class AppConfig(QConfig):
    onlineMvQuality = OptionsConfigItem("Online", "MvQuality", MvQuality.FULL_HD, OptionsValidator(MvQuality),
                                        EnumSerializer(MvQuality))
