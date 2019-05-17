import cv2,numpy,time, os, random, threading

#超时3秒未完成则重启
def time_out(func):
    def wrap_func(*args,**kwargs):
        restart = lambda : func(*args,**kwargs)
        timer = threading.Timer(3, restart)
        timer.start()
        func(*args,**kwargs)
        timer.cancel()
    return wrap_func

#ADB命令手机截屏，并发送到当前目录,opencv读取文件并返回
@time_out
def screen_shot():
    a = "adb shell screencap -p sdcard/screen.jpg"
    b = "adb pull sdcard/screen.jpg"
    for row in [a, b]:
        time.sleep(0.5)
        os.system(row)



# ADB命令点击屏幕，参数pos为目标坐标
def touch(pos):
    x, y = pos
    a = "adb shell input touchscreen tap {0} {1}" .format(x, y)
    os.system(a)

#蜂鸣报警器，参数n为鸣叫资料
def alarm(n):
    frequency = 1500
    last = 500

    for n in range(n):
        print(frequency,last)
        time.sleep(0.05)

#按【文件内容，匹配精度，名称】格式批量读取要查找的目标图片，精度统一为0.85，名称为文件名
def load_imgs():
    mubiao = {}
    path = os.getcwd() + '/jpg'
    file_list = os.listdir(path)

    for file in file_list:
        name = file.split('.')[0]
        file_path = path + '/' + file
        a = [ cv2.imread(file_path) , 0.8, name]
        mubiao[name] = a

    return mubiao

def mathc_img(image,Target,value):
    img_rgb = cv2.imread(image)
    img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
    template = cv2.imread(Target,0)
    w, h = template.shape[::-1]
    res = cv2.matchTemplate(img_gray,template,cv2.TM_CCOEFF_NORMED)
    threshold = value
    loc = numpy.where( res >= threshold)
    for pt in zip(*loc[::-1]):
        cv2.rectangle(img_rgb, pt, (pt[0] + w, pt[1] + h), (7,249,151), 2)
    cv2.imshow('Detected',img_rgb)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

 #在背景查找目标图片，以列表形式返回查找目标的中心坐标，
 #screen是截屏图片，want是找的图片【按上面load_imgs的格式】，show是否以图片形式显示匹配结果【调试用】
def locate(screen, want, show=0):
    loc_pos = []
    want, treshold, c_name = want[0], want[1], want[2]
    result = cv2.matchTemplate(screen, want, cv2.TM_CCOEFF_NORMED)
    location = numpy.where(result >= treshold)

    h,w = want.shape[:-1]

    n,ex,ey = 1,0,0
    for pt in zip(*location[::-1]):
        x,y = pt[0] + int(w/2), pt[1] + int(h/2)
        if (x-ex) + (y-ey) < 15:  #去掉邻近重复的点
            continue
        ex,ey = x,y

        cv2.circle(screen, (x, y), 10, (0, 0, 255), 3)

        x,y = int(x), int(y)
        loc_pos.append([x, y])

    if show:  #在图上显示寻找的结果，调试时开启
        cv2.imshow('we get', screen)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    if len(loc_pos) == 0:
        print(c_name, 'not found')

    return loc_pos

#裁剪图片以缩小匹配范围，screen为原图内容，upleft、downright是目标区域的左上角、右下角坐标
def cut(screen, upleft, downright):

    a,b = upleft
    c,d = downright
    screen = screen[b:d,a:c]

    return screen

#随机偏移坐标，防止游戏的外挂检测。p是原坐标，w、n是目标图像宽高，返回目标范围内的一个随机坐标
def cheat(p, w, h):
    a,b = p
    w, h = int(w/3), int(h/3)
    c,d = random.randint(-w, w),random.randint(-h, h)
    e,f = a + c, b + d
    y = [e, f]
    return(y)

#随机延迟，防止游戏外挂检测，延迟时间范围为【x, y】秒之间
def wait(x=0.2, y=0.5):
    t = random.uniform(x, y)
    time.sleep(t)



def findTextRegion(img):
    region = []

    # 1. 查找轮廓
    contours, hierarchy = cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # 2. 筛选那些面积小的
    for i in range(len(contours)):
        cnt = contours[i]
        # 计算该轮廓的面积
        area = cv2.contourArea(cnt)

        # 面积小的都筛选掉
        if(area < 1000):
            continue

        # 轮廓近似，作用很小
        epsilon = 0.001 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)

        # 找到最小的矩形，该矩形可能有方向
        rect = cv2.minAreaRect(cnt)
        print("rect is: ")
        print(rect)

        # box是四个点的坐标
        box = cv2.boxPoints(rect)
        box = numpy.int0(box)

        # 计算高和宽
        height = abs(box[0][1] - box[2][1])
        width = abs(box[0][0] - box[2][0])

        # 筛选那些太细的矩形，留下扁的
        if(height > width * 1.2):
            continue

        region.append(box)

    return region

def preprocess(gray):
    # 1. Sobel算子，x方向求梯度
    sobel = cv2.Sobel(gray, cv2.CV_8U, 1, 0, ksize = 3)
    # 2. 二值化
    ret, binary = cv2.threshold(sobel, 0, 255, cv2.THRESH_OTSU+cv2.THRESH_BINARY)

    # 3. 膨胀和腐蚀操作的核函数
    element1 = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 9))
    element2 = cv2.getStructuringElement(cv2.MORPH_RECT, (24, 6))

    # 4. 膨胀一次，让轮廓突出
    dilation = cv2.dilate(binary, element2, iterations = 1)

    # 5. 腐蚀一次，去掉细节，如表格线等。注意这里去掉的是竖直的线
    erosion = cv2.erode(dilation, element1, iterations = 1)

    # 6. 再次膨胀，让轮廓明显一些
    dilation2 = cv2.dilate(erosion, element2, iterations = 3)

    # 7. 存储中间图片
    cv2.imwrite("binary.png", binary)
    cv2.imwrite("dilation.png", dilation)
    cv2.imwrite("erosion.png", erosion)
    cv2.imwrite("dilation2.png", dilation2)

    return dilation2

def detect(img, show):
    # 1.  转化成灰度图
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 2. 形态学变换的预处理，得到可以查找矩形的图片
    dilation = preprocess(gray)

    # 3. 查找和筛选文字区域
    region = findTextRegion(dilation)

    # 4. 用绿线画出这些找到的轮廓
    for box in region:
        cv2.drawContours(img, [box], 0, (0, 255, 0), 2)

    cv2.namedWindow("img", cv2.WINDOW_NORMAL)

    if show:
        cv2.imshow("img", img)

        # 带轮廓的图片
        cv2.imwrite("contours.png", img)

        cv2.waitKey(0)
        cv2.destroyAllWindows()

