import os
import asyncio
from pyrogram.types import Message
from pyrogram.errors import MessageNotModified, FloodWait
from bot.tgclient import aio
from bot.settings import bot_set
from bot.logger import LOGGER

current_user = []
user_details = {
    'user_id': None, 'name': None, 'user_name': None, 
    'r_id': None, 'chat_id': None, 'provider': None,
    'bot_msg': None, 'link': None, 'override' : None
}

async def fetch_user_details(msg: Message, reply=False) -> dict:
    details = user_details.copy()
    details['user_id'] = msg.from_user.id
    details['name'] = msg.from_user.first_name
    details['user_name'] = msg.from_user.username if msg.from_user.username else msg.from_user.mention()
    details['r_id'] = msg.reply_to_message.id if reply else msg.id
    details['chat_id'] = msg.chat.id
    try: details['bot_msg'] = msg.id
    except: pass
    return details

async def check_user(uid=None, msg=None, restricted=False) -> bool:
    # Admin access
    if uid in bot_set.admins or (msg and msg.from_user and msg.from_user.id in bot_set.admins):
        return True
    
    # Group Access Check
    if msg and msg.chat.type in ['group', 'supergroup']:
        return True
    
    # Public access check
    if bot_set.bot_public:
        return True
        
    return False

async def antiSpam(uid=None, cid=None, revoke=False) -> bool:
    if revoke:
        if bot_set.anti_spam == 'CHAT+':
            if cid in current_user: current_user.remove(cid)
        elif bot_set.anti_spam == 'USER':
            if uid in current_user: current_user.remove(uid)
    else:
        if bot_set.anti_spam == 'CHAT+':
            if cid in current_user: return True
            else: current_user.append(cid)
        elif bot_set.anti_spam == 'USER':
            if uid in current_user: return True
            else: current_user.append(uid)
        return False

async def send_message(user, item, itype='text', caption=None, markup=None, chat_id=None, meta=None):
    if not isinstance(user, dict):
        user = await fetch_user_details(user)
    target_chat = chat_id if chat_id else user['chat_id']

    try:
        if itype == 'text':
            msg = await aio.send_message(chat_id=target_chat, text=item, reply_to_message_id=user['r_id'], reply_markup=markup, disable_web_page_preview=True)
        elif itype == 'doc':
            msg = await aio.send_document(chat_id=target_chat, document=item, caption=caption, reply_to_message_id=user['r_id'])
        elif itype == 'audio':
            msg = await aio.send_audio(chat_id=target_chat, audio=item, caption=caption, duration=int(meta['duration']), performer=meta['artist'], title=meta['title'], thumb=meta['thumbnail'], reply_to_message_id=user['r_id'])
        elif itype == 'pic':
            msg = await aio.send_photo(chat_id=target_chat, photo=item, caption=caption, reply_to_message_id=user['r_id'])
        
        # Channel Dump Logic
        if bot_set.dump_channel and itype in ['audio', 'doc']:
            try:
                await aio.send_copy(chat_id=bot_set.dump_channel, from_chat_id=msg.chat.id, message_id=msg.id)
            except Exception as e:
                LOGGER.error(f"Channel Dump Error: {e}")

    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await send_message(user, item, itype, caption, markup, chat_id, meta)
    return msg

async def edit_message(msg:Message, text, markup=None, antiflood=True):
    try:
        return await msg.edit_text(text=text, reply_markup=markup, disable_web_page_preview=True)
    except MessageNotModified:
        return None
    except FloodWait as e:
        if antiflood:
            await asyncio.sleep(e.value)
            return await edit_message(msg, text, markup, antiflood)
        return None
