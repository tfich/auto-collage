import datetime
import math
import os
from io import BytesIO
from random import randint

import requests
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

BOT_TOKEN = os.environ.get('BOT_TOKEN')


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
    channelID = os.environ.get('DEFAULT_CHANNEL_ID')
    while not channelID:
        inputChannelID = input(
            '\nWhich channel do you wan\'t to pull from?\nPlease enter the channel\'s ID\n> ')
        if len(inputChannelID) > 16:
            channelID = inputChannelID
        else:
            print('Please input a valid channel ID!\n')

    return channelID


def getOverlayColor():
    hexColor = os.environ.get('DEFAULT_OVERLAY_COLOR')
    while not hexColor:
        inputHex = input(
            '\nWhat color overlay do you want?\nExample: #B4FBB8\nAnswer \'None\' for no overlay.\n> '
        )
        if inputHex.lower() == 'none':
            return None
        if len(inputHex) in range(6, 7):
            hexColor = inputHex
        else:
            print('Please input a valid hexadecimal color!\n')

    return tuple(int(hexColor.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))


def getForegroundImageUrl():
    imageUrl = os.environ.get('DEFAULT_IMG_URL')
    while not imageUrl:
        inputImgUrl = input(
            '\nWhat is the link to your foreground image?\nAnswer \'None\' for no foreground image.\n> '
        )
        if inputImgUrl.lower() == 'none':
            return None
        if inputImgUrl.startswith('http'):
            imageUrl = inputImgUrl
        else:
            print('Please input a valid image url!\n')

    return imageUrl


def fetchMessages(channelID, lastMsgID):
    messages = []
    reqLen = 100
    reqCount = 1
    while reqLen == 100:
        url = f'https://discordapp.com/api/channels/{channelID}/messages?limit=100'
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

    maxImages = int(os.environ.get('MAX_IMAGES'))
    if len(images) > maxImages:
        images = images[-maxImages:]
        print(f'{len(images)} images found - only {maxImages} are being used!\n')
    else:
        print(f'{len(images)} images found!\n')

    return images


def createCollage(images, overlayColor, foregroundImgUrl):
    baseImageSize = (1920, 1080)
    (baseWidth, baseHeight) = baseImageSize
    baseImage = Image.new('RGBA', baseImageSize, 'white')

    gridDimensions = (6, 6)  # width, height
    (gridWith, gridHeight) = gridDimensions
    splitWidth, splitHeight = baseWidth / gridWith, baseHeight / gridHeight

    imageIndex = len(images) - 1
    numIterations = math.ceil(len(images) / (gridWith * gridHeight))
    for _ in range(numIterations):
        for numCols in range(gridWith):
            for numRows in range(gridHeight):
                posX = \
                    randint(numCols * splitWidth, numCols * (splitWidth + 1))
                posY = \
                    randint(numRows * splitHeight, numRows * (splitHeight + 1))
                layerPosition = (posX, posY)

                image = images[imageIndex]
                res = requests.get(image['url'])
                discordImg = Image.open(BytesIO(res.content))
                discordImg.convert('RGBA')

                layerSize = (baseWidth // 4, baseHeight // 4)
                discordImg.thumbnail(layerSize)

                baseImage.paste(discordImg, layerPosition)
                print(
                    f'[Img {len(images) - imageIndex}/{len(images)}] Discord image applied as layer...'
                )
                imageIndex -= 1

                if imageIndex == -1:
                    break

            if imageIndex == -1:
                break

    if overlayColor:
        opacityMultiplier = float(os.environ.get('DEFAULT_OVERLAY_OPACITY'))
        opacity = int(255 * opacityMultiplier)
        overlay = Image.new('RGBA', baseImageSize, overlayColor+(opacity,))
        baseImage = Image.alpha_composite(baseImage, overlay)

    if foregroundImgUrl:
        res = requests.get(foregroundImgUrl)
        foregroundImg = Image.open(BytesIO(res.content))
        foregroundImgSize = (baseWidth // 3, baseHeight // 3)
        foregroundImg.thumbnail(foregroundImgSize)
        foregroundImg.convert('RGBA')
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
        print('Please add a BOT_TOKEN to your .env!')
        quit()

    lastMsgID = getLastMsgID()
    channelID = getChannelID()
    overlayColor = getOverlayColor()
    foregroundImgUrl = getForegroundImageUrl()

    print('\nPulling messages from Discord...')
    messages = fetchMessages(channelID, lastMsgID)
    print(f'\nPulled {len(messages)} messages total!')

    images = parseImages(messages)

    print('Creating collage...')
    createCollage(images, overlayColor, foregroundImgUrl)
