from module.base.button import ButtonGrid
from module.base.decorator import Config
from module.base.utils import *

from module.equipment.equipment import Equipment
from module.equipment.assets import *


EQUIP_INFO_BAR = ButtonGrid(
    origin=(723, 111), delta=(94, 0), button_shape=(76, 76), grid_shape=(5, 1), name="EQUIP_INFO_BAR"
)

SIM_VALUE = 0.90


class EquipmentChange(Equipment):

    def __init__(self, config, device):
        super().__init__(config, device=device)
        self.equip_list = {}

    def record_equipment(self):
        '''
        通过强化界面记录装备
        '''

        self.device.screenshot()

        self.equip_sidebar_ensure(1)

        for index in range(0, 5):

            while 1:
                self.device.screenshot()

                if self.appear(EQUIPMENT_OPEN, interval=3):
                    self.device.click(EQUIP_INFO_BAR[(index, 0)])
                    # time.sleep(1)
                    continue
                if self.appear_then_click(UPGRADE_ENTER, interval=3):
                    continue
                if self.appear(UPGRADE_ENTER_CHECK, interval=3):
                    self.wait_until_stable(EQUIP_SAVE)
                    self.equip_list[index] = self.image_area(EQUIP_SAVE)
                    self.device.click(UPGRADE_QUIT)
                    self.wait_until_stable(UPGRADE_QUIT)
                    break

            # self.equip_list[index].show()
            # print(index)

    def equipment_take_on(self):
        '''
        通过之前记录的装备装备回来
        '''
        self.device.screenshot()

        self.equip_sidebar_ensure(2)

        self.ensure_no_info_bar(1)

        for index in range(0, 5):

            enter_button = globals()[
                'EQUIP_TAKE_ON_{index}'.format(index=index)]

            while 1:

                self.device.screenshot()

                if self.appear(enter_button, offset=(5,5), threshold=0.90, interval=2):
                    self.device.click(enter_button)
                    self._find_equip(index)
                    self.wait_until_stable(UPGRADE_QUIT)
                    continue

                if self.info_bar_count():
                    self.ensure_no_info_bar(1)
                    break

    @Config.when(DEVICE_CONTROL_METHOD='minitouch')
    def _equipment_swipe(self, distance=190):
        # Distance of two commission is 146px
        p1, p2 = random_rectangle_vector(
            (0, -distance), box=(620, 67, 1154, 692), random_range=(-20, -5, 20, 5))
        self.device.drag(p1, p2, segments=2, shake=(25, 0),
                         point_random=(0, 0, 0, 0), shake_random=(-5, 0, 5, 0))
        self.device.sleep(0.3)
        self.device.screenshot()

    @Config.when(DEVICE_CONTROL_METHOD=None)
    def _equipment_swipe(self, distance=300):
        # Distance of two commission is 146px
        p1, p2 = random_rectangle_vector(
            (0, -distance), box=(620, 67, 1154, 692), random_range=(-20, -5, 20, 5))
        self.device.drag(p1, p2, segments=2, shake=(25, 0),
                         point_random=(0, 0, 0, 0), shake_random=(-5, 0, 5, 0))
        self.device.sleep(0.3)
        self.device.screenshot()

    def _equip_equipment(self, index, point, offset=(100, 100)):
        '''
        in: 仓库
        do：装，退
        '''

        while 1:
            self.device.screenshot()

            if self.appear(EQUIPPING_OFF, interval=5):
                self.device.click(
                    Button(button=(point[0], point[1], point[0]+offset[0], point[1]+offset[1]), color=None, area=None))
                continue
            if self.appear_then_click(EQUIP_CONFIRM, interval=3):
                continue
            if self.info_bar_count():
                self.wait_until_stable(UPGRADE_QUIT)
                break

    def _find_equip(self, index):
        '''
        in: 仓库
        do: 找
        '''
        self.wait_until_stable(UPGRADE_QUIT, skip_first_screenshot=False)

        self.equipping_set(False)

        res = cv2.matchTemplate(np.array(self.device.screenshot()), np.array(
            self.equip_list[index]), cv2.TM_CCOEFF_NORMED)
        _, sim, _, point = cv2.minMaxLoc(res)

        if sim > SIM_VALUE:
            self._equip_equipment(index, point)
            return

        for _ in range(0, 15):
            print(_)
            self._equipment_swipe()

            res = cv2.matchTemplate(np.array(self.device.screenshot()), np.array(
                self.equip_list[index]), cv2.TM_CCOEFF_NORMED)
            _, sim, _, point = cv2.minMaxLoc(res)

            if sim > SIM_VALUE:
                self._equip_equipment(index, point)
                break
            if self.appear(EQUIPMENT_SCROLL_BOTTOM):
                print(23333)
                break

        return