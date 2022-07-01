#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
    VSavedBot - бот, который кидает сохранёнки из тг в вк
    Weescr, 2022
"""

import os, hashlib
from aiogram import Bot, Dispatcher, executor, types
from vkwave.api import API
from vkwave.client import AIOHTTPClient

import db, vkontakte
from urllib.parse import parse_qs

MY_CHANNEL = "@weescr_users"
TOKEN = os.getenv("TELEGRAM_API_TOKEN")

class VSavedBot:
    
    def __init__(self, tg_token: str) -> None:
        self.APIS = {}
        self.bot = Bot(token = tg_token)
    
    async def get_vk_api(self, vk_token: str) -> API: # None в случае нерабочего токена
        api_session = API(tokens = vk_token, clients = AIOHTTPClient())
        api = api_session.get_context()
        try:
            await api.photos.get_albums()
        except:
            return None
        else:
            return api
    
    async def catch_picture(self, message: types.Message) -> None:
        user_id = message.from_user.id

        if not self.APIS.get(str(user_id)):
            saved_vk_token = db.get_vk_token_by_telegram_id(user_id)
            if saved_vk_token:
                api_obj = await self.get_vk_api(vk_token = saved_vk_token)
                up_obj = vkontakte.UploadSavedPicture(api_obj = api_obj)
                self.APIS.setdefault(f"{user_id}", up_obj)
            else:
                await message.reply("Сначала авторизуйтесь")
                return

        await message.reply("Вот тут я фотку начинаю скачивать")
        filename = str(message.photo[-1].file_id) + '.jpg'
        await self.bot.download_file_by_id(message.photo[-1].file_id, filename )
        await self.APIS.get(str(user_id)).upload(filename)
        await message.reply("Скачал")
    
    async def await_vk_token(self, message: types.Message) -> None:
        user_id = message.from_user.id
        username = message.from_user.username or "ID_Скрыт"

        parsed_url = parse_qs(message.text)
        vk_token = parsed_url.get("https://oauth.vk.com/blank.html#access_token")
        print("так называемый вк токен", vk_token)

        if not vk_token:
            await message.reply("Нет, это не сработает")
        else:
            api_obj = await self.get_vk_api(vk_token = vk_token)
            
            if not api_obj:
                await message.reply("Неправильный токен")
            else:

                db.add(f"{user_id}", vk_token[0])
                up_obj = vkontakte.UploadSavedPicture(api_obj = api_obj)
                self.APIS.setdefault(f"{user_id}", up_obj)

                n = db.get_counter()
                await self.bot.send_message(MY_CHANNEL, f"@{username} поддерживает молодых разработчиков, броу респект\nПользователей @VSavedBot: {n}")
                await message.reply("Да, это сработает")
    
    async def send_welcome(self, message: types.Message) -> None:
        user_id = message.from_user.id

        if not db.get_vk_token_by_telegram_id(user_id):
            await message.reply("0, да вы новенький!")
        else:
            await message.reply("Вы уже авторизованы")

    async def how_many_users_online(self, message: types.Message) -> None:
        n = db.get_counter()
        await message.answer(f"Пользователей: {n}")
    
    def start(self) -> None:
        dp = Dispatcher(self.bot)
        dp.register_message_handler(self.send_welcome, commands = ['start'])
        dp.register_message_handler(self.how_many_users_online, commands = ['users'])
        dp.register_message_handler(self.await_vk_token, content_types = ['text'])
        dp.register_message_handler(self.catch_picture, content_types = ['photo'])
        executor.start_polling(dp, skip_updates = True)

if __name__ == '__main__':
    b = VSavedBot(TOKEN)
    b.start()