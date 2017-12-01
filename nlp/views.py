from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views import generic

from . import utils

# Create your views here.


class IndexView(generic.TemplateView):
    template_name = 'nlp/index.html'


def process(request):
    msg = request.GET.get('msg')
    results = utils.processing_procedure(msg)
    return JsonResponse({'results': results})
