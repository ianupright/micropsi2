__author__ = 'rvuine'

from PIL import Image, ImageDraw
import random

SIZE = 10


def create_shape(shape=None):
    matrix = []
    for i in range(0, SIZE):
        matrix.append([])
        for j in range(0, SIZE):
            matrix[i].append(random.random() * 2)

    im = Image.new("RGB", (len(matrix), len(matrix[0])))
    for x in range(0, len(matrix)):
        for y in range(0, len(matrix[0])):
            cl = int(matrix[x][y] * 255.0)
            im.putpixel((x, y), (cl, cl, cl))

    if shape is None:
        pass
    elif shape == "vertical":
        draw_vertical_shape(im)

    for i in range(0, SIZE):
        for j in range(0, SIZE):
            matrix[i][j] = float(im.getpixel((i, j))[0]) / 255.0

    return matrix


def draw_vertical_shape(im):
    draw = ImageDraw.Draw(im)
    xshift = random.randint(-2, 2)
    yshift = random.randint(-2, 2)
    thickness = random.randint(2, 4)
    for i in range(1, thickness):
        draw.line([(4+xshift+i, 0+yshift), (4+xshift+i, 10+yshift)], fill="#000000")
    #im.save("/Users/rvuine/Desktop/pix.png")
