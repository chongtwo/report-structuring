from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views import generic

from . import utils

# Create your views here.


class IndexView(generic.TemplateView):
    template_name = 'nlp/index.html'


def process(request):
    msg = request.GET.get('msg')
    results, sentences_list = utils.processing_procedure(msg)
    content = {'sentences':sentences_list,
               'results': results,
               'origin_msg': msg}
    return JsonResponse(content, json_dumps_params={'ensure_ascii': False})
