"""
OBJETIVO: Prueba estática del modelo de IA para Detección de Fatiga (Desgaste Laboral)
INTEGRANTES: CASTRO LUNA CESAR ARMANDO, EPINOZA BRAVO LUDWING, LOZANO CARDONA ANGEL JOSUE
PROYECTO: Sistema de registro de Asistencias y Desgaste Laboral
"""

import os
import urllib.request
import cv2
from ai_processor import FatigueDetector

def download_sample_image(filename, url):
    if not os.path.exists(filename):
        print(f"Descargando imagen de prueba: {filename}...")
        urllib.request.urlretrieve(url, filename)

def main():
    print("=== INICIANDO VALIDACIÓN PREVIA DE IA ===")
    
    # Crear carpeta data si no existe
    if not os.path.exists('data'):
        os.makedirs('data')
        
    # URL de imagen de prueba (rostro de frente)
    test_img_path = 'data/test_face.jpg'
    download_sample_image(test_img_path, 'https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg')
    
    detector = FatigueDetector(ear_threshold=0.25)
    
    # Cargar imagen local
    print(f"Cargando imagen: {test_img_path}")
    image = cv2.imread(test_img_path)
    
    if image is None:
        print("ERROR: No se pudo cargar la imagen.")
        return
        
    print("Procesando imagen con MediaPipe Face Mesh...")
    is_fatigued, ear_val, out_img = detector.process_image(image)
    
    estado = "FATIGA DETECTADA" if is_fatigued else "VIGILIA (DESPIERTO)"
    print(f"Resultado -> EAR: {ear_val:.3f} | Estado: {estado}")
    
    # Opcional: mostrar imagen si estamos en entorno gráfico
    # cv2.imshow("Prueba Estatica IA", out_img)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
    
    # Guardar resultado para verificar
    res_path = 'data/resultado_test.jpg'
    cv2.imwrite(res_path, out_img)
    print(f"Imagen procesada guardada en: {res_path}")
    print("=== VALIDACIÓN COMPLETADA ===")

if __name__ == "__main__":
    main()
