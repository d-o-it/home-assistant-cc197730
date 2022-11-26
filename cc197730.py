"""Conrad Components 197730 implementation."""

import logging
import asyncio
import asyncio.tasks
import serialio

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = 3.0
_SEND_READ_TIMEOUT = 0.05


class CC197330State:
    def __init__(self, card: int, relay: int, is_on: int) -> None:
        self._card = card
        self._relay = relay
        self._is_on = True if is_on is 1 else False

    @property
    def card(self):
        """The card property."""
        return self._card

    @property
    def relay(self):
        """The relay property."""
        return self._relay

    @property
    def is_on(self):
        """The is_on property."""
        return self._is_on


class CC197730:
    def __init__(self, serial: serialio) -> None:
        self.serial = serial
        self.serial_lock = asyncio.Lock()

    async def __send_and_read(self, data: bytearray) -> bytearray:
        _LOGGER.debug("Sending %s", data.hex())
        await self.serial.write(data)
        await asyncio.sleep(_SEND_READ_TIMEOUT)

        recv = await self.serial.read(1024)
        _LOGGER.debug("Received %s", recv.hex())
        return recv

    async def __open_send_init(self) -> bytearray:
        await self.serial.open()
        return await self.__send_and_read(bytearray([1, 1, 1, 1]))

    def __frame_valid(self, data: bytearray, start: int) -> bool:
        if start + 4 > len(data):
            return False

        return data[start + 3] == (data[start] ^ data[start + 1] ^ data[start + 2])

    def __response_valid(
        self, data: bytearray, cmd: int, card: int, relay: int
    ) -> bool:
        if len(data) % 4 != 0:
            return False

        for i in range(0, len(data), 4):
            if not self.__frame_valid(data, i):
                return False

            if data[i] == 255 - cmd:
                if data[i + 1] != card:
                    return False
                if ((data[i + 2] >> (relay - 1)) & 1) != (1 if cmd == 6 else 0):
                    return False

        return True

    async def __get_all_states(self) -> list:
        data = await self.__open_send_init()
        if len(data) < 8 or data[0] != 254:
            raise Exception("Invalid respose")

        card_count = 0
        card_version = 0
        for i in range(0, 256, 4):
            if i + 4 > len(data):
                break

            if data[i] == 1:
                if data[i + 1] == 0:
                    card_count = 255
                else:
                    card_count = data[i + 1] - 1
                    card_version = data[i + 2]
                break

        _LOGGER.info(
            "%i card with version %i.%i detected",
            card_count,
            card_version / 10,
            card_version % 10,
        )

        data = await self.__send_and_read(bytearray([2, 0, 0, 2]))
        if len(data) < 8 or data[0] != 253:
            raise Exception("Invalid respose")

        devices = []
        for i in range(0, card_count * 4, 4):
            for j in range(8):
                devices.append(
                    CC197330State(data[i + 1], j + 1, (data[i + 2] >> j) & 1)
                )

        return devices

    async def __worker(self, cmd: int, card: int, relay: int) -> bytearray:
        data = await self.__open_send_init()
        if len(data) < 4 or data[0] != 254:
            raise Exception("Invalid respose")

        relay_bits = (1 << (relay - 1)) & 255
        cksum = (cmd ^ card ^ relay_bits) & 255
        data = await self.__send_and_read(bytearray([cmd, card, relay_bits, cksum]))
        if len(data) < 4 or not self.__response_valid(data, cmd, card, relay):
            raise Exception("Invalid respose")

        return data

    async def __process(self, func) -> bytearray:
        await self.serial_lock.acquire()
        try:
            return await asyncio.wait_for(func, _TIMEOUT)
        finally:
            await self.serial.close()
            self.serial_lock.release()

    async def get_states(self) -> list:
        """Get all states."""
        _LOGGER.info("Get all states")
        return await self.__process(self.__get_all_states())

    async def set(self, card: int, relay: int):
        """Set `relay` of `card`."""
        _LOGGER.info("Switch on card %i relay %i", card, relay)
        if not 0 < relay < 9:
            raise Exception("invalid relay number")

        await self.__process(self.__worker(6, card & 255, relay & 255))

    async def clear(self, card: int, relay: int):
        """Clear `relay` of `card`."""
        _LOGGER.info("Switch off card %i relay %i", card, relay)
        if not 0 < relay < 9:
            raise Exception("invalid relay number")

        await self.__process(self.__worker(7, card & 255, relay & 255))
