import asyncio
import logging
import os

import aiofiles
from aiohttp import web

CHUNK_SIZE = 100 * 1024

logging.basicConfig(level=logging.DEBUG)


async def archive(request):
    files_folder_name = 'test_photos'
    archive_name = 'photos.zip'
    archive_hash = request.match_info.get('archive_hash')
    files_path = f'{os.getcwd()}/{files_folder_name}/{archive_hash}/'

    if not os.path.exists(files_path):
        return web.HTTPNotFound(
            text="<html><body>The archive does not exist or has been deleted.</body></html>",
            content_type="text/html"
        )

    response = web.StreamResponse()
    response.headers['Content-Disposition'] = f'attachment; filename={archive_name}'

    await response.prepare(request)

    archive_process = await asyncio.create_subprocess_exec(
        'zip', '-r', '-', '.',
        cwd=files_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        limit=CHUNK_SIZE,
    )

    try:
        while not archive_process.stdout.at_eof():
            archive_chunk = await archive_process.stdout.read(CHUNK_SIZE)
            await response.write(archive_chunk)
            logging.debug(u'Sending archive chunk ...')
            await asyncio.sleep(3)

    except asyncio.CancelledError:
        archive_process.terminate()
        logging.info(u'Download was interrupted')
        raise

    except BaseException as exception:
        archive_process.terminate()
        logging.exception(exception)
        raise

    finally:
        await archive_process.communicate()
        return response


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
