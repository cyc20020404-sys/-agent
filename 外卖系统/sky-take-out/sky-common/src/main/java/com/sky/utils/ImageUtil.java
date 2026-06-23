package com.sky.utils;


import com.sky.entity.Dish;
import com.sky.entity.OrderDetail;
import com.sky.entity.Setmeal;
import com.sky.vo.DishVO;
import com.sky.vo.SetmealVO;
import lombok.extern.slf4j.Slf4j;

import java.util.List;

@Slf4j
public class ImageUtil {

    /**
     * 处理菜品VO的图片URL
     *
     * @param dishVOs 菜品VO列表
     */
    public static void processDishVOImage(List<DishVO> dishVOs) {
        if (dishVOs == null || dishVOs.isEmpty()) {
            return;
        }

        for (DishVO dishVO : dishVOs) {
            if (dishVO.getImage() != null) {
                dishVO.setImage(UrlUtil.buildImageUrl(dishVO.getImage()));
            }
        }
    }

    /**
     * 处理菜品实体的图片URL
     *
     * @param dishes 菜品实体列表
     */
    public static void processDishImage(List<Dish> dishes) {
        if (dishes == null || dishes.isEmpty()) {
            return;
        }

        for (Dish dish : dishes) {
            if (dish.getImage() != null) {
                dish.setImage(UrlUtil.buildImageUrl(dish.getImage()));
            }
        }
    }

    /**
     * 处理菜品实体的图片URL
     *
     * @param setmeals 菜品实体列表
     */
    public static void processSetmealImage(List<Setmeal> setmeals) {
        if (setmeals == null || setmeals.isEmpty()) {
            return;
        }

        for (Setmeal setmeal : setmeals) {
            if (setmeal.getImage() != null) {
                setmeal.setImage(UrlUtil.buildImageUrl(setmeal.getImage()));
            }
        }
    }


    /**
     * 处理订单明细的图片URL
     *
     * @param orderDetails 订单明细列表
     */
    public static void processOrderDetailImage(List<OrderDetail> orderDetails) {
        if (orderDetails == null || orderDetails.isEmpty()) {
            return;
        }

        for (OrderDetail orderDetail : orderDetails) {
            if (orderDetail.getImage() != null) {
                orderDetail.setImage(UrlUtil.buildImageUrl(orderDetail.getImage()));
            }
        }
    }

    /**
     * 处理套餐VO的图片URL
     *
     * @param setmealVOs 套餐VO列表
     */
    public static void processSetmealVOImage(List<SetmealVO> setmealVOs) {
        if (setmealVOs == null || setmealVOs.isEmpty()) {
            return;
        }

        for (SetmealVO setmealVO : setmealVOs) {
            if (setmealVO.getImage() != null) {
                setmealVO.setImage(UrlUtil.buildImageUrl(setmealVO.getImage()));
            }
        }
    }

    /**
     * 处理单个菜品VO的图片URL
     *
     * @param dishVO 菜品VO
     */
    public static void processDishVOImage(DishVO dishVO) {
        if (dishVO != null && dishVO.getImage() != null) {
            dishVO.setImage(UrlUtil.buildImageUrl(dishVO.getImage()));
        }
    }

    /**
     * 处理单个套餐VO的图片URL
     *
     * @param setmealVO 套餐VO
     */
    public static void processSetmealVOImage(SetmealVO setmealVO) {
        if (setmealVO != null && setmealVO.getImage() != null) {
            setmealVO.setImage(UrlUtil.buildImageUrl(setmealVO.getImage()));
        }
    }

    /**
     * 处理单个订单明细的图片URL
     *
     * @param orderDetail 订单明细
     */
    public static void processOrderDetailImage(OrderDetail orderDetail) {
        if (orderDetail != null && orderDetail.getImage() != null) {
            orderDetail.setImage(UrlUtil.buildImageUrl(orderDetail.getImage()));
        }
    }
}