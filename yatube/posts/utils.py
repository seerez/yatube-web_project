from django.core.paginator import Paginator

LIMIT_POST = 10


def paginator(request, queryset):
    paginator = Paginator(queryset, LIMIT_POST)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
