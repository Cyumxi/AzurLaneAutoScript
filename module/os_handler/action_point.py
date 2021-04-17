from module.base.button import ButtonGrid
from module.base.utils import *
from module.logger import logger
from module.ocr.ocr import Digit, DigitCounter
from module.os_handler.assets import *
from module.statistics.item import ItemGrid
from module.ui.assets import OS_CHECK
from module.ui.ui import UI

OCR_ACTION_POINT_REMAIN = Digit(ACTION_POINT_REMAIN, letter=(255, 219, 66), name='OCR_ACTION_POINT_REMAIN')
OCR_ACTION_POINT_BUY_REMAIN = DigitCounter(
    ACTION_POINT_BUY_REMAIN, letter=(148, 251, 99), name='OCR_ACTION_POINT_BUY_REMAIN')
ACTION_POINT_GRID = ButtonGrid(
    origin=(323, 274), delta=(173, 0), button_shape=(115, 115), grid_shape=(4, 1), name='ACTION_POINT_GRID')
ACTION_POINT_ITEMS = ItemGrid(ACTION_POINT_GRID, templates={}, amount_area=(30, 71, 91, 92))
ACTION_POINTS_COST = {
    1: 5,
    2: 10,
    3: 15,
    4: 20,
    5: 30,
    6: 40,
}
ACTION_POINTS_BUY = {
    1: 4000,
    2: 2000,
    3: 2000,
    4: 1000,
    5: 1000,
}


class ActionPointLimit(Exception):
    pass


class ActionPointHandler(UI):
    _action_point_amount = [0, 0, 0, 0]
    _action_point_current = 0

    def _is_in_action_point(self):
        return self.appear(ACTION_POINT_USE, offset=(20, 20))

    def action_point_use(self):
        # Find the button, button may be movable.
        self.appear(ACTION_POINT_USE, offset=(20, 20))
        self.device.click(ACTION_POINT_USE)

    def action_point_get_current(self):
        """
        Returns:
            int: Total action points, including ap boxes.
        """
        items = ACTION_POINT_ITEMS.predict(self.device.image, name=False, amount=True)
        amount = [item.amount for item in items]
        current = OCR_ACTION_POINT_REMAIN.ocr(self.device.image)
        action_point = np.sum(np.array(amount) * (0, 20, 50, 200)) + current
        oil = amount[0]

        logger.info(f'Action points: {action_point}, oil: {oil}')
        self._action_point_current = current
        self._action_point_amount = amount
        return action_point

    @staticmethod
    def action_point_get_cost(zone, pinned):
        """
        Args:
            zone (Zone): Zone to enter.
            pinned (str): Zone type. Available types: DANGEROUS, SAFE, OBSCURE, LOGGER, STRONGHOLD.

        Returns:
            int: Action points that will cost.
        """
        cost = ACTION_POINTS_COST[zone.hazard_level]
        if zone.is_port:
            cost = 0
        if pinned == 'DANGEROUS':
            cost *= 2
        if pinned == 'STRONGHOLD':
            cost = 200

        return cost

    def action_point_get_active_button(self):
        """
        Returns:
            int: 0 to 3. 0 for oil, 1 for 20 ap box, 2 for 50 ap box, 3 for 100 ap box.
        """
        for index, item in enumerate(ACTION_POINT_GRID.buttons()):
            area = item.area
            color = get_color(self.device.image, area=(area[0], area[3] + 5, area[2], area[3] + 10))
            # Active button will turn blue.
            # Active: 196, inactive: 118 ~ 123.
            if color[2] > 160:
                return index

        logger.warning('Unable to find an active action point box button')
        return 1

    def action_point_set_button(self, index, skip_first_screenshot=True):
        """
        Args:
            index (int): 0 to 3. 0 for oil, 1 for 20 ap box, 2 for 50 ap box, 3 for 100 ap box.
            skip_first_screenshot (bool):

        Returns:
            bool: If success.
        """
        for _ in range(3):
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.action_point_get_active_button() == index:
                return True
            else:
                self.device.click(ACTION_POINT_GRID[index, 0])
                self.device.sleep(0.3)

        logger.warning('Failed to set action point button after 3 trial')
        return False

    def action_point_buy(self, preserve=1000):
        """
        Use oil to buy action points.

        Args:
            preserve (int): Oil to preserve.

        Returns:
            bool: If reach the limit to buy action points this week
        """
        self.action_point_set_button(0)
        if not self.image_color_count(ACTION_POINT_BUY_REMAIN, color=(148, 251, 99), threshold=180, count=20):
            logger.info('Reach the limit to buy action points this week')
            return False

        current, _, _ = OCR_ACTION_POINT_BUY_REMAIN.ocr(self.device.image)
        cost = ACTION_POINTS_BUY[current]
        oil = self._action_point_amount[0]
        logger.info(f'Buy action points will cost {cost}, current oil: {oil}, preserve: {preserve}')
        if oil >= cost + preserve:
            self.action_point_use()
        else:
            logger.info('Not enough oil to buy')
        return True

    def action_point_quit(self, skip_first_screenshot=True):
        """
        Pages:
            in: ACTION_POINT_USE
            out: page_os
        """
        self.ui_click(ACTION_POINT_CANCEL, check_button=OS_CHECK, skip_first_screenshot=skip_first_screenshot)

    def handle_action_point(self, zone, pinned):
        """
        Args:
            zone (Zone): Zone to enter.
            pinned (str): Zone type. Available types: DANGEROUS, SAFE, OBSCURE, LOGGER, STRONGHOLD.

        Returns:
            bool: If handled.

        Raises:
            ActionPointLimit: If not having enough action points.

        Pages:
            in: ACTION_POINT_USE
        """
        if not self._is_in_action_point():
            return False

        cost = self.action_point_get_cost(zone, pinned)
        for _ in range(12):
            # End
            if self.action_point_get_current() < self.config.OS_ACTION_POINT_PRESERVE:
                logger.info(f'Reach the limit of action points, preserve={self.config.OS_ACTION_POINT_PRESERVE}')
                self.action_point_quit()
                raise ActionPointLimit
            if self._action_point_current >= cost:
                logger.info('Having enough action points')
                self.action_point_quit()
                return True

            # Get more action points
            if self.config.ENABLE_OS_ACTION_POINT_BUY:
                self.action_point_buy(preserve=self.config.STOP_IF_OIL_LOWER_THAN)
            for index in [3, 2, 1]:
                if self._action_point_amount[index] > 0:
                    self.action_point_set_button(index)
                    self.action_point_use()

        logger.warning('Failed to get action points after 12 trial')
        return False