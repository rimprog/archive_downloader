import asyncio
import os

import aiofiles
from aiohttp import web


async def archive(request):
    files_folder_name = 'test_photos'
    archive_name = 'photos.zip'
    archive_hash = request.match_info.get('archive_hash')
    files_path = f'{os.getcwd()}/{files_folder_name}/{archive_hash}/'
    if os.path.exists(files_path):
        response = web.StreamResponse()
        response.headers['Content-Disposition'] = f'attachment; filename={archive_name}'

        await response.prepare(request)

        archive_process = await asyncio.create_subprocess_exec(
            'zip', '-r', '-', f'./',
            stdout=asyncio.subprocess.PIPE,
            cwd=files_path,
        )

        while not archive_process.stdout.at_eof():
            archive_chunk = await archive_process.stdout.read(102400)
            await response.write(archive_chunk)

        return response

    else:
        return web.HTTPNotFound(
            text="<html><body>The archive does not exist or has been deleted.</body></html>",
            content_type="text/html"
        )


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app)
