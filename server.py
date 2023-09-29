import argparse
import asyncio
import logging
import os
import pathlib

import aiofiles
from aiohttp import web
from pathvalidate import sanitize_filepath

CHUNK_SIZE = 100 * 1024

parser = argparse.ArgumentParser(
    description='Microservice for archive downloading'
)
parser.add_argument('--logging', help='Turn on|off logging',
                    action=argparse.BooleanOptionalAction, type=bool, default=True)
parser.add_argument('--archive_delay', help='Turn on|off delay during archive process',
                    action=argparse.BooleanOptionalAction, type=bool, default=False)
parser.add_argument('--path_to_files_folder', help='Path to folder with files for archiving',
                    default=f'{os.getcwd()}/test_photos/', type=pathlib.Path)
args = parser.parse_args()

if not args.path_to_files_folder.exists():
    raise argparse.ArgumentTypeError(
        f'Path to folder with files for archiving does not exist: {args.path_to_files_folder}'
    )

if args.logging:
    logging.basicConfig(level=logging.DEBUG)


async def archive(request):
    archive_name = 'photos.zip'
    archive_hash = request.match_info.get('archive_hash')
    files_path = sanitize_filepath(
        os.path.join(args.path_to_files_folder, archive_hash)
    )

    if not os.path.exists(files_path):
        return web.HTTPNotFound(
            text="<html><body>The archive does not exist or has been deleted.</body></html>",
            content_type="text/html"
        )

    response = web.StreamResponse()
    response.enable_chunked_encoding()
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

            if args.archive_delay:
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
