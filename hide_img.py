import base64, os, math
from io import BytesIO
from PIL import Image
from hoshino import Service, aiorequests #删除本行和下面的sv 以及使用requests来替换aiorequests后可以在none中使用
from nonebot import on_command, CommandSession

#none使用需要删除本处，其实我没写帮助信息的触发（
sv = Service('幻影坦克', help_='''发送[@bot]隐藏图片开始制作幻影坦克
依次发送两张图片，第一张为表图，是白色背景时显示的图片
第二张图片为隐图，是黑色背景时显示的图片''')

headers = {"User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9.1.6) ",
           "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "Accept-Language": "zh-cn"
           }
_path = os.path.dirname(__file__)
def get_all_img_url(event): #从消息中提取图片URL
    all_url = []
    for i in event["message"]:
        if i["type"] == "image":
            all_url.append(i["data"]["url"])
    return all_url


async def save_img(image_url): #保存图片 #none使用的话尽量不要异步，这里异步的话可能会报错，没有验证过
    try:
        if len(image_url) == 0:
            return None
        for url in image_url:
            response = await aiorequests.get(url, headers=headers) #none使用的话此处改为使用requests，去掉await
            image = Image.open(BytesIO(await response.content))
        return image
    except Exception as e:
        print(repr(e))
        return None


def make_image(up_img, hide_img):
    #先获取两张图片中宽度较大的宽度
    max_size = (max(up_img.size[0], hide_img.size[0]), 0)
    #将图片依据较大的宽度等比例处理
    up_img = up_img.resize((max_size[0], int(up_img.size[1] * (max_size[0] / up_img.size[0]))),Image.ANTIALIAS)
    hide_img = hide_img.resize((max_size[0], int(hide_img.size[1] * (max_size[0] / hide_img.size[0]))),Image.ANTIALIAS)
    #获取处理后生成图片的大小
    max_size = (max_size[0], max(up_img.size[1], hide_img.size[1]))
    
    if hide_img.size[1] == up_img.size[1]: #大小相等直接转为灰度图片
        up_img = up_img.convert('L')
        hide_img = hide_img.convert('L')
    elif max_size[1] == hide_img.size[1]: #这两个elif都是对图片进行大小补全后再转为灰度图片
        up_img_temp = Image.new('RGBA',(max_size),(255,255,255,255))
        up_img_temp.paste(up_img,(0, (max_size[1] - up_img.size[1]) // 2))
        up_img = up_img_temp.convert('L')
        hide_img = hide_img.convert('L')
    elif max_size[1] == up_img.size[1]:
        hide_img_temp = Image.new('RGBA',(max_size),(0,0,0,255))
        hide_img_temp.paste(hide_img,(0, (max_size[1] - hide_img.size[1]) // 2))
        up_img = up_img.convert('L')
        hide_img = hide_img_temp.convert('L')

    
    out = Image.new('RGBA',(max_size),(255,255,255,255)) #生成一个空的用于输出的图片
    for i in range(up_img.size[0]):
        for k in range(up_img.size[1]): #遍历读取每一个像素点
            La = (up_img.getpixel((i,k)) / 512) + 0.5 #512是256*2，采用256是为了避免La-Lb=1的情况，而且基本不会损失图片信息
            Lb = hide_img.getpixel((i,k)) / 512       # a/2 +0.5是为了区分明部和暗部，这样明部都在[0.5,1),暗部都在[0,0.5)，互不干扰
            R = int((255 * Lb) / (1 - (La - Lb)))
            a = int((1 - (La - Lb)) * 255) #这里是套用公式 公式可以见b站专栏 隐藏图原理(https://www.bilibili.com/read/cv9474134/)
            out.putpixel((i, k), (R,R,R,a)) #将用于输出的图片每个像素点处理成需要的颜色和透明度

    buf = BytesIO()
    out.save(buf, format='PNG')
    base64_str = f'base64://{base64.b64encode(buf.getvalue()).decode()}'
    return f'[CQ:image,file={base64_str}]'


img = []
send_times = 0
@on_command('hide_image', only_to_me=True, aliases=['隐藏图片'])
async def hide_image(session: CommandSession):
    global img
    global send_times
    session.get('', prompt='发送要上传的图片,暂不支持gif')
    image = await save_img(get_all_img_url(session.ctx))
    if image:
        img.append(image)
    else:
        send_times += 1
    if send_times >= 3:
        await session.send('过多次未发送图片，已自动停止')
        img = []
        send_times = 0
        return
    if len(img) == 0:
        session.pause('请上传第一张图片')
    elif len(img) == 1:
        session.pause('请上传第二张图片')
    elif len(img) == 2:
        await session.send('正在合成图片，请稍后')
        msg = make_image(img[0],img[1]).strip()
        img = []
        await session.finish(msg)


