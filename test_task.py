from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from django.utils.date import date

from .models import (
    Orders,
    Favorites,
    Orderresponsible,
    Ordercomresponsible,
    Comments,
    CustomersList,
    Costs,
    Approvedlists,
)


class OrderList(LoginRequiredMixin, View):
    def get(self, request):
        orders = Orders.objects.all()
        search_params = request.user.search

        if search_params.search:
            orders = orders.filter(
                Q(name__icontains=search_params.search)
                | Q(searchowners__icontains=search_params.search)
            )
        else:
            if search_params.goal:
                orders = orders.filter(goal=True)

            if search_params.favorite:
                fav_orders = Favorites.objects.filter(
                    user=request.user
                ).values_list("order__orderid", flat=True)

                orders = orders.filter(orderid__in=fav_orders)

            if search_params.manager:
                responsible_orders = Orderresponsible.objects.filter(
                    user=search_params.manager
                ).values_list("orderid__orderid", flat=True)

                com_responsible_orders = (
                    Ordercomresponsible.objects.filter(
                        user=search_params.manager
                    )
                    .exclude(orderid__orderid__in=responsible_orders)
                    .values_list("orderid__orderid", flat=True)
                )

                orders = orders.filter(
                    orderid__in=set(responsible_orders).union(
                        com_responsible_orders
                    )
                )

            if search_params.stage:
                orders = orders.filter(stageid=search_params.stage)

            if search_params.company:
                orders = orders.filter(
                    Q(cityid=None) | Q(cityid=search_params.company)
                )

            if search_params.customer:
                orders = orders.filter(
                    searchowners__icontains=search_params.customer
                )

        if request.GET.get("action") == "count":
            return JsonResponse({"count": orders.count()})

        orders = orders.order_by("-reiting")[
            int(request.GET["start"]) : int(request.GET["stop"])
        ]
        customers, lastcontact, resp, favorite, task = [], [], [], [], []

        for order in orders:
            resp.append(Orderresponsible.objects.filter(orderid=order.orderid)
                        )
            customers_list = CustomersList.objects.filter(
                orderid=order.orderid
            ).order_by("customerid__title")

            customers.append(customers_list)

            lastcontact.append(
                Comments.objects.filter(orderid=order)
                .order_by("-createdat")
                .first()
                .createdat
                if Comments.objects.filter(orderid=order).exists()
                else ""
            )

            task.append(
                Comments.objects.filter(orderid=order, istask=1)
                .exclude(complete=1)
                .count()
            )

            favorite.append(
                Favorites.objects.filter(
                    user=request.user, order=order
                ).exists()
            )

        context = {
            "orders": zip(
                orders, customers, favorite, lastcontact, task, resp
            ),
            "Today": date.today(),
        }
        return render(request, "main/orders_list.html", context)


class CostList(LoginRequiredMixin, View):
    def get(self, request):
        costs = Costs.objects.all()
        search_params = request.user.search

        if search_params.search:
            costs = costs.filter(
                Q(description__icontains=search_params.search)
                | Q(section__icontains=search_params.search)
                | Q(orderid__name__icontains=search_params.search)
            )
        else:
            if search_params.goal:
                costs = costs.filter(orderid__goal=True)

            if search_params.favorite:
                fav_orders = Favorites.objects.filter(
                    user=request.user
                ).values_list("order__orderid", flat=True)
                costs = costs.filter(orderid__in=fav_orders)

            if search_params.manager:
                costs = costs.filter(user=search_params.manager)

            if search_params.stage:
                costs = costs.filter(orderid__stageid=search_params.stage)

            if search_params.company:
                costs = costs.filter(
                    Q(orderid__cityid=None)
                    | Q(orderid__cityid=search_params.company)
                )

            if search_params.customer:
                costs = costs.filter(
                    orderid__searchowners__icontains=search_params.customer
                )

        if request.GET.get("action") == "count":
            return JsonResponse({"count": costs.count()})

        costs = costs.order_by("-createdat")[
            int(request.GET["start"]) : int(request.GET["stop"])
        ]
        appr = [Approvedlists.objects.filter(cost_id=cost) for cost in costs]

        context = {"costs": zip(costs, appr), "Today": date.today()}
        return render(request, "main/cost_list.html", context)
