import geopandas as gpd
from rasterio.mask import mask
import rasterio
import numpy as np
import os
from shapely.geometry import shape
import fiona

# Caminho para a imagem geotiff
caminho_imagem = r"C:\Sensix\teste_python\imagem_daninha\solo exposto.tif"

# Caminho para o shapefile de máscara
caminho_mascara = r"C:\Sensix\teste_python\imagem_daninha\contshx.shp"

# Caminho para salvar o resultado binário
caminho_resultado_binario = r"C:\Users\danie\Downloads\resultado9.tif"

# Caminho para salvar o resultado em shapefile
caminho_saida_shp = r"C:\Users\danie\Downloads\resultado9.shp"

# Fator de redução de resolução desejado (número de pixels a serem agrupados)
fator_reducao = 5

# Condições de processamento
min_value_condition_1 = 10
factor_adjustment_2 = 2.0
pixel_size = 10
block_size = 542

def gerar_binario(caminho_imagem, caminho_mascara, caminho_resultado, fator_reducao):
    # Lê o shapefile de máscara usando geopandas
    mascara = gpd.read_file(caminho_mascara)

    # Abre o arquivo geotiff com rasterio
    with rasterio.open(caminho_imagem) as src:
        # Realiza o recorte usando a função mask
        imagem_recortada, transformacao = mask(src, mascara.geometry, crop=True)

        # Obtém os metadados da imagem original
        meta = src.meta.copy()

        # Calcula a nova resolução
        nova_resolucao_x = abs(meta['transform'][0]) * fator_reducao
        nova_resolucao_y = abs(meta['transform'][4]) * fator_reducao

        # Calcula as novas dimensões da imagem
        nova_largura = int(meta['width'] / fator_reducao)
        nova_altura = int(meta['height'] / fator_reducao)

        # Redimensiona a imagem usando a média dos pixels próximos
        imagem_reduzida = np.zeros((meta['count'], nova_altura, nova_largura), dtype=np.uint8)

        for i in range(meta['count']):
            for y in range(nova_altura):
                for x in range(nova_largura):
                    imagem_reduzida[i, y, x] = np.mean(imagem_recortada[i, y*fator_reducao:(y+1)*fator_reducao,
                                                                       x*fator_reducao:(x+1)*fator_reducao]).astype(np.uint8)

    # Aplica as condições diretamente na imagem reduzida para gerar o binário
    binario = ((imagem_reduzida[1] > imagem_reduzida[0]) & (imagem_reduzida[2] <= 115))

    # Atualiza os metadados para o binário
    meta.update({"driver": "GTiff",
                 "height": nova_altura,
                 "width": nova_largura,
                 "count": 1,
                 "dtype": 'uint8',
                 "nodata": 0,
                 "transform": rasterio.Affine(nova_resolucao_x, transformacao.b, transformacao.c,
                                              transformacao.d, -nova_resolucao_y, transformacao.f),
                 "crs": src.crs})

    # Salva o resultado binário no novo arquivo geotiff
    with rasterio.open(caminho_resultado, "w", **meta) as dest:
        dest.write(binario.astype(np.uint8) * 255, 1)

    return binario, meta

def binario_para_shp(binario, meta, caminho_saida_shp):
    # Poligoniza o binário e salva em um shapefile
    shapes = ({'properties': {'raster_val': int(v)}, 'geometry': s}
              for i, (s, v) in enumerate(
                rasterio.features.shapes(binario.astype(np.uint8), transform=meta['transform'])))

    with fiona.open(caminho_saida_shp, 'w', crs=meta['crs'], driver='ESRI Shapefile',
                    schema={'properties': [('raster_val', 'int')], 'geometry': 'Polygon'}) as shp:
        shp.writerecords(shapes)

# Gerar binário
binario, meta = gerar_binario(caminho_imagem, caminho_mascara, caminho_resultado_binario, fator_reducao)

# Converter binário para shapefile
binario_para_shp(binario, meta, caminho_saida_shp)

print("Processo concluído. O resultado foi salvo em:", caminho_saida_shp)