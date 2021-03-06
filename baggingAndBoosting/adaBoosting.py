#!/usr/bin/python
# -*- coding: UTF-8 -*-

#   data-analysis
#   adaBoosting.py

"""
    Description:
    author : zhangjingbo 
    Date:    2018/12/25
"""
import numpy as np
import math


def loadDataSet(fileName):
    # 获取 feature 的数量, 便于获取
    numFeat = len(open(fileName).readline().split('\t'))
    dataArr = []
    labelArr = []
    fr = open(fileName)
    for line in fr.readlines():
        lineArr = []
        curLine = line.strip().split('\t')
        for i in range(numFeat - 1):
            lineArr.append(float(curLine[i]))
        dataArr.append(lineArr)
        labelArr.append(float(curLine[-1]))
    return dataArr, labelArr


def adaBoostTrainDS(dataArr, labelArr, numIt=40):
    """adaBoostTrainDS(adaBoost训练过程放大)
    Args:
        dataArr   特征标签集合
        labelArr  分类标签集合
        numIt     实例数
    Returns:
        weakClassArr  弱分类器的集合
        aggClassEst   预测的分类结果值
    """
    weakClassArr = []
    m = dataArr.shape[0]
    # 初始化 D，设置每个样本的权重值，平均分为m份
    D = np.mat(np.ones((m, 1)) / m)
    aggClassEst = np.mat(np.zeros((m, 1)))
    for i in range(numIt):
        # 得到决策树的模型
        bestStump, error, classEst = build_stump(dataArr, labelArr, D)

        # alpha目的主要是计算每一个分类器实例的权重(组合就是分类结果)
        # 计算每个分类器的alpha权重值
        alpha = float(0.5 * np.log((1.0 - error) / max(error, 1e-16)))
        bestStump['alpha'] = alpha
        # store Stump Params in Array
        weakClassArr.append(bestStump)

        print("alpha=%s, classEst=%s, bestStump=%s, error=%s " % (alpha, classEst.T, bestStump, error))
        # 分类正确：乘积为1，不会影响结果，-1主要是下面求e的-alpha次方
        # 分类错误：乘积为 -1，结果会受影响，所以也乘以 -1
        expon = np.multiply(-1 * alpha * np.mat(labelArr).T, classEst)
        print('(-1取反)预测值expon=', expon.T)
        # 计算e的expon次方，然后计算得到一个综合的概率的值
        # 结果发现： 判断错误的样本，D中相对应的样本权重值会变大。
        D = np.multiply(D, np.exp(expon))
        D = D / D.sum()

        # 预测的分类结果值，在上一轮结果的基础上，进行加和操作
        print('当前的分类结果：', alpha * classEst.T)
        aggClassEst += alpha * classEst
        print("叠加后的分类结果aggClassEst: ", aggClassEst.T)
        # sign 判断正为1， 0为0， 负为-1，通过最终加和的权重值，判断符号。
        # 结果为：错误的样本标签集合，因为是 !=,那么结果就是0 正, 1 负
        aggErrors = np.multiply(np.sign(aggClassEst) != np.mat(labelArr).T, np.ones((m, 1)))
        errorRate = aggErrors.sum() / m
        # print "total error=%s " % (errorRate)
        if errorRate == 0.0:
            break
    return weakClassArr, aggClassEst


def build_stump(data_arr, class_labels, D):
    """
    得到决策树的模型 (这个比较重要，需要看懂）
    :param data_arr: 特征标签集合
    :param class_labels: 分类标签集合
    :param D: 最初的特征权重值
    :return: bestStump    最优的分类器模型
            min_error     错误率
            best_class_est  训练后的结果集
    """
    data_mat = np.mat(data_arr)
    label_mat = np.mat(class_labels).T

    m, n = np.shape(data_mat)
    num_steps = 10.0
    best_stump = {}
    best_class_est = np.mat(np.zeros((m, 1)))
    # 无穷大
    min_err = np.inf
    for i in range(n):
        range_min = data_mat[:, i].min()
        range_max = data_mat[:, i].max()
        step_size = (range_max - range_min) / num_steps
        for j in range(-1, int(num_steps) + 1):
            for inequal in ['lt', 'gt']:
                thresh_val = (range_min + float(j) * step_size)
                predicted_vals = stump_classify(data_mat, i, thresh_val, inequal)
                err_arr = np.mat(np.ones((m, 1)))
                err_arr[predicted_vals == label_mat] = 0
                # 这里是矩阵乘法
                weighted_err = D.T * err_arr
                '''
                dim            表示 feature列
                thresh_val      表示树的分界值
                inequal        表示计算树左右颠倒的错误率的情况
                weighted_error  表示整体结果的错误率
                best_class_est    预测的最优结果 （与class_labels对应）
                '''
                # print('split: dim {}, thresh {}, thresh inequal: {}, the weighted err is {}'.format(
                #     i, thresh_val, inequal, weighted_err
                # ))
                if weighted_err < min_err:
                    min_err = weighted_err
                    best_class_est = predicted_vals.copy()
                    best_stump['dim'] = i
                    best_stump['thresh'] = thresh_val
                    best_stump['ineq'] = inequal
    # best_stump 表示分类器的结果，在第几个列上，用大于／小于比较，阈值是多少 (单个弱分类器)
    return best_stump, min_err, best_class_est


def stump_classify(data_mat, dimen, thresh_val, thresh_ineq):
    """
    (将数据集，按照feature列的value进行 二分法切分比较来赋值分类)
    :param data_mat: Matrix数据集
    :param dimen: 特征的哪一个列
    :param thresh_val: 特征列要比较的值
    :param thresh_ineq:
    :return: np.array
    """
    ret_array = np.ones((np.shape(data_mat)[0], 1))
    # data_mat[:, dimen] 表示数据集中第dimen列的所有值
    # thresh_ineq == 'lt'表示修改左边的值，gt表示修改右边的值
    # （这里其实我建议理解为转换左右边，就是一棵树的左右孩子，可能有点问题。。。待考证）
    if thresh_ineq == 'lt':
        ret_array[data_mat[:, dimen] <= thresh_val] = -1.0
    else:
        ret_array[data_mat[:, dimen] > thresh_val] = -1.0
    return ret_array
