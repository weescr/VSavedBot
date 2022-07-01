import os
import json
import aiohttp

from vkwave.api import API
from vkwave.client import AIOHTTPClient

ALBUM_DESCRIPTION = "LOL"
ALBUM_TITLE = "SYNC_QUEUE"


class UploadSavedPicture:

	def __init__(self, api_obj: API):
		self.api = api_obj
		self.sync_album = None
	
	async def get_sync_queue_album(self):
		response = await self.api.photos.get_albums()
		sync_album = None
		for album in response.response.items:
			if album.title == ALBUM_TITLE:
				sync_album = album.id
		return sync_album
	
	async def create_sync_queue_album(self):
		response = await self.api.photos.create_album(
			title = ALBUM_TITLE,
			description = ALBUM_DESCRIPTION,
			privacy_view = 'only_me',
			privacy_comment = 'only_me',
			comments_disabled = 1,
		)
		return response.response.id
	
	async def check_sync_album(self):
		if not self.sync_album:
			self.sync_album = await self.get_sync_queue_album()
			if not self.sync_album:
				self.sync_album = await self.create_sync_queue_album()
	
	async def upload_pic_to_sync_album(self, filename):

		await self.check_sync_album() # 1
		result = await self.api.photos.get_upload_server(album_id = self.sync_album) # 2
		url_to_upload = result.response.upload_url

		if not os.access(filename, os.R_OK):
			return None, None
		else:
			f = open(filename, 'rb')

			async with aiohttp.ClientSession() as session:
				async with session.post(url_to_upload, data = {'file':f}) as resp:
					data = await resp.read()
			
			hashrate = json.loads(data)
			
			result = await self.api.photos.save( #3
				album_id = self.sync_album,
				server = hashrate['server'],
				photos_list = hashrate['photos_list'],
				hash = hashrate['hash']
			)
		
			return result.response[0].owner_id, result.response[0].id
	
	async def upload(self, filename) -> bool:
		owner_id, photo_id = await self.upload_pic_to_sync_album(filename) # 4
		await self.api.photos.copy(owner_id = owner_id, photo_id = photo_id) # 5
		await self.api.photos.delete(owner_id = owner_id, photo_id = photo_id) #6
		os.remove(filename)
		return True