import datetime
import math
import os
from io import BytesIO
from random import randint

import requests
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

# add BOT_TOKEN to your .env file or paste as a string here
BOT_TOKEN = os.environ.get('BOT_TOKEN') or ''


def getLastMsgID():
    while True:
        inputDate = input(
            '\nHow far back to you wan\'t to fetch your images?\nExample: 03/29/20\n> '
        )
        if len(inputDate) == 8:
            break
        else:
            print('\nPlease input a valid date!\n')
    [month, day, year] = inputDate.split('/')
    date = datetime.datetime(2000 + int(year), int(month), int(day))

    return int((date.timestamp() * 1000) - 1420070400000) << 22


def getChannelID():
    while True:
        inputChannelID = input(
            '\nWhich channel do you wan\'t to pull from?\nPlease enter the channel\'s ID\n> ')
        if len(inputChannelID) > 16:
            return inputChannelID
        else:
            print('Please input a valid channel ID!\n')


def getOverlayColor():
    while True:
        inputHex = input(
            '\nWhat color overlay do you want?\nExample: #B4FBB8\nAnswer \'None\' for no overlay.\n> '
        ).lstrip('#')
        if inputHex.lower() == 'none':
            return None
        if len(inputHex) == 6:
            return tuple(int(inputHex[i:i+2], 16) for i in (0, 2, 4))
        else:
            print('Please input a valid hexadecimal color!\n')


def getForegroundImageUrl():
    while True:
        inputImgUrl = input(
            '\nWhat is the link to your foreground image?\nAnswer \'None\' for no foreground image.\n> '
        )
        if inputImgUrl.lower() == 'none':
            return None
        if inputImgUrl.startswith('http'):
            return inputImgUrl
        else:
            print('Please input a valid image url!\n')


def fetchMessages(channelID, lastMsgID):
    messages = []
    reqLen = 100
    reqCount = 1
    while reqLen == 100:
        url = f'https://discordapp.com/api/channels/{channelID}/messages?limit={100}'
        if int(lastMsgID) > 0:
            url += f'&after={lastMsgID}'
        pulledMsgs = requests.get(
            url, headers={'Authorization': 'Bot ' + BOT_TOKEN}).json()
        lastMsgID = pulledMsgs[0]['id']
        reqLen = len(pulledMsgs)
        messages.append(pulledMsgs)
        print(f'[Req {reqCount}] Pulled {reqLen} messages!')
        reqCount += 1

    return [x for y in messages for x in y]


def parseImages(messages):
    images = []
    for message in messages:
        for attachment in message['attachments']:
            if attachment['width'] and attachment['height']:
                images.append({
                    'url': attachment['url'],
                    'size': (attachment['width'], attachment['height'])
                })

    return images


def createCollage(images, overlayColor, foregroundImgUrl):
    baseImageSize = (1920, 1080)
    (baseWidth, baseHeight) = baseImageSize
    baseImage = Image.new('RGBA', baseImageSize, 'white')

    x, y = 0, 0
    scalar = 100
    for i in range(len(images)):
        res = requests.get(images[i]['url'])
        discordImg = Image.open(BytesIO(res.content))
        discordImg.convert('RGBA')

        layerSize = (baseWidth // 3, baseHeight // 3)
        discordImg.thumbnail(layerSize)

        layerPosition = (randint(x, x + scalar), randint(y, y + scalar))
        baseImage.paste(discordImg, layerPosition)
        print(f'[Img {i+1}/{len(images)}] Discord image applied as layer...')

        x += scalar
        y += scalar
        if x > baseWidth:
            x = 0
        if y > baseHeight:
            y = 0

    if overlayColor:
        opacity = int(255 * .45)
        overlay = Image.new('RGBA', baseImageSize, overlayColor+(opacity,))
        baseImage = Image.alpha_composite(baseImage, overlay)

    if foregroundImgUrl:
        res = requests.get(foregroundImgUrl)
        foregroundImg = Image.open(BytesIO(res.content))
        foregroundImgSize = (baseWidth // 5, baseHeight // 5)
        foregroundImg.thumbnail(foregroundImgSize)
        foregroundPosition = (
            ((baseWidth - foregroundImg.size[0]) // 2),
            ((baseHeight - foregroundImg.size[1]) // 2)
        )
        baseImage.paste(foregroundImg, foregroundPosition)

    outDir = 'output.png'
    baseImage.save(outDir)
    print(f'\nImage saved as {outDir}!\n')


def getPosition(baseImageSize):
    (width, height) = baseImageSize
    return (randint(0, width), randint(0, height))


if __name__ == "__main__":
    if not BOT_TOKEN:
        print('\nPlease Load BOT_TOKEN in .env or at the top of this file!\n')
        quit()

    lastMsgID = getLastMsgID()
    channelID = getChannelID()
    overlayColor = getOverlayColor()
    print(overlayColor)
    foregroundImgUrl = getForegroundImageUrl()

    print('\nPulling messages from Discord...')
    messages = fetchMessages(channelID, lastMsgID)
    print(f'\nPulled {len(messages)} messages total!')

    images = parseImages(messages)
    print(f'Found {len(images)} valid image urls!\n')

    print('Creating collage...')
    createCollage(images, overlayColor, foregroundImgUrl)
