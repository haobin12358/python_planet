# -*- coding: utf-8 -*-
import random
import math
import numpy as np
import cv2
import os
from flask import current_app
from datetime import datetime
from planet.common.request_handler import gennerc_log

class GithubAvatarGenerator:
    '''
    Github default avatar is a 420*420 image contains 5*5 block vertex.
    Each block is a 70*70 square.
    The width of the frame around block vertex is 35px.
    This is an example avatar.
    https://raw.githubusercontent.com/josephzxy/pic/master/example_github_avatar.png
    This class aims at generating a github-avatar-like avatars.
    Usage:
        - Initialize this class
        - Call get_randowm_avatar()
    '''

    avatar_width = 420  # the length of line of the avatar
    block_vertex_dimension = 5  # the dimension of block vertex
    block_width = 70  # the length of line of block
    background_color = [230, 230, 230]  # the brackground color
    frame_width = 35  # the width of frame surrounding block vertex
    # some color that might be approiprate for the color of block.
    color_pool_rgb = (
        (170, 205, 102),
        (159, 255, 84),
        (209, 206, 0),
        (255, 255, 0),
        (47, 107, 85),
        (47, 255, 173),
        (0, 173, 205),
        (8, 101, 139),
        (180, 180, 238),
        (106, 106, 255),
        (155, 211, 255),
        (204, 50, 153),
        (101, 119, 139)
    )

    def _get_avatar_vertex(self):
        '''
        Generate a vertex of which each value is a boolean value.
        This 5*5 vertex denotes the strcture of 5*5 block vertex in github avatar
        '''
        # get 5*5 2d array full of False
        avatar_vertex = np.empty((self.block_vertex_dimension, self.block_vertex_dimension), dtype=np.bool)

        for row in avatar_vertex:
            for i in range(math.ceil(self.block_vertex_dimension / 2)):
                row[i] = True if random.randint(0, 1) == 1 else False
        # copy left half to right half
        for row in avatar_vertex:
            for i in range(math.floor(self.block_vertex_dimension / 2)):
                row[self.block_vertex_dimension - 1 - i] = row[i]

        return avatar_vertex

    def _get_avatar_data(self):
        '''
        Generate a 3d array contains color info in each pixel in the avatar
        '''
        # fill the whole img with the background
        avatar_data = np.zeros((self.avatar_width, self.avatar_width, 3), dtype=np.uint8)
        avatar_data[:][:] = self.background_color

        rand_color_index = random.randint(0, len(self.color_pool_rgb) - 1)
        rand_color = self.color_pool_rgb[rand_color_index]

        avatar_vertex = self._get_avatar_vertex()

        # add blocks according to avatar vertex
        for i in range(len(avatar_vertex)):
            for j in range(len(avatar_vertex[i])):
                is_True = avatar_vertex[i][j]
                if is_True:
                    up_left_point = (self.frame_width + i * self.block_width, self.frame_width + j * self.block_width)
                    for k in range(self.block_width):
                        for l in range(self.block_width):
                            lvl1 = k + up_left_point[0]
                            lvl2 = l + up_left_point[1]
                            avatar_data[lvl1][lvl2] = rand_color
                else:
                    continue

        return avatar_data

    def get_random_avatar(self):
        img = self._get_avatar_data()
        cv2.imshow('My pic', img)
        cv2.waitKey()

    def save_avatar(self, filepath):
        time_now = datetime.now()
        year = str(time_now.year)
        month = str(time_now.month)
        day = str(time_now.day)
        img = self._get_avatar_data()
        newPath = os.path.join(current_app.config['BASEDIR'], 'img', 'defaulthead', year, month, day)
        if not os.path.isdir(newPath):
            os.makedirs(newPath)
        # newPath = newPath + filepath + '.png'
        newPath = os.path.join(newPath, filepath + '.png')
        gennerc_log(newPath)
        cv2.imwrite(newPath, img)
        data = '/img/defaulthead/{}/{}/{}/{}'.format(year, month, day, filepath + '.png')
        return data


if __name__ == '__main__':
    gen = GithubAvatarGenerator()
    # gen.get_random_avatar()
    gen.save_avatar(r'D:\myrandomhead.jpg')