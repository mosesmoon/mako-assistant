# Asistente MAKO — Guía de funciones

[English](en.md) · [台灣正體中文](zh_TW.md) · [简体中文](zh_CN.md) · [日本語](ja.md) · [Deutsch](de.md) · [Français](fr.md) · **Español** · [Italiano](it.md) · [ไทย](th.md) · [Tiếng Việt](vi.md) · [Bahasa Melayu](ms.md) · [हिन्दी](hi.md)

El **Asistente MAKO** es una herramienta gráfica para escritorio Linux que activa o desactiva con un clic la **generación de fotogramas de MAKO Renderer (Mako FG)** en tus juegos de Steam, sin editar a mano ningún archivo de configuración.

## ¿Para quién es?

En Steam Deck, en el modo Juego, MAKO tiene un plugin de Decky que permite ajustarlo todo dentro del juego. En un **PC de escritorio o portátil con Linux normal** (por ejemplo Arch, Fedora o Ubuntu con KDE Plasma o GNOME), conseguir que un juego use MAKO suele obligarte a hacer todo esto a mano:

1. Añadir `~/.local/bin/mako-launch %command%` a las opciones de lanzamiento de Steam del juego (Propiedades → Opciones de lanzamiento) sin romper las opciones que ya había.
2. Averiguar el nombre del programa que el juego **ejecuta realmente** (muchos juegos abren primero un lanzador, y los juegos de Unreal Engine ejecutan un `*-Shipping.exe`).
3. Crear un perfil de juego en los ajustes de MAKO y escribir los procesos asociados correctos (`active_in`).
4. Repetirlo todo cuando una actualización del juego cambia la ruta o el nombre del ejecutable.
5. Iniciar el juego sin saber con seguridad si la generación de fotogramas está funcionando de verdad.

El Asistente MAKO reúne estos pasos en un solo botón y, mientras un juego está en ejecución, muestra qué funciones de MAKO están **realmente** activas.

## Antes de empezar

> ⚠ **El Asistente MAKO no incluye MAKO Renderer ni lo instala por ti.** Solo gestiona los ajustes de MAKO.

Haz esto primero:

1. **Instala MAKO Renderer (versión independiente)** siguiendo las instrucciones de instalación del propio MAKO. Después de instalarlo, debe existir `~/.local/bin/mako-launch`.
2. **Abre MAKO UI una vez** para crear los ajustes predeterminados. Así se crean `~/.config/mako-render/conf.toml` y el perfil predeterminado `mako`. Cada perfil de juego que crea el Asistente MAKO es una copia de este perfil predeterminado.
3. **Instala Steam.** Se admiten el paquete nativo (`~/.local/share/Steam`, `~/.steam`) y las versiones Flatpak y Snap.

Asegúrate de haber hecho todo lo anterior y de que MAKO funciona antes de instalar Mako FG en un juego con el Asistente MAKO.

Opcional: **Decky Loader.** Con él, las opciones de lanzamiento se pueden aplicar en directo mientras Steam está abierto, sin cerrarlo (consulta «Cómo se escriben las opciones de lanzamiento» más abajo).

## Funciones

### 1. Escaneo automático de la biblioteca de Steam

- La primera vez que lo abres, escanea **todas** tus bibliotecas de Steam (incluidas las de otros discos). Después puedes pulsar «⟳ Volver a escanear juegos de Steam».
- Las herramientas como Proton y Steam Linux Runtime se excluyen, así que solo aparecen juegos.
- Los nombres de los juegos se muestran con su nombre localizado oficial de Steam en el idioma de la interfaz y se ordenan según la costumbre de ese idioma.
- Cada juego muestra su portada, sus opciones de lanzamiento actuales, su perfil de MAKO y las rutas del ejecutable detectadas.

### 2. «Instalar Mako FG» con un clic

Al pulsar «Instalar Mako FG», la herramienta:

- **Añade la opción de lanzamiento** `~/.local/bin/mako-launch %command%` a las opciones de lanzamiento de Steam del juego y **conserva lo que ya había**. Por ejemplo, `FOO=1 %command% -dx11` pasa a ser `FOO=1 ~/.local/bin/mako-launch %command% -dx11`.
- **Detecta el ejecutable real del juego** a partir de la información de la aplicación de Steam. Tiene en cuenta los lanzadores (en ese caso busca el programa real del juego en la carpeta de instalación) y los `*-Shipping.exe` de Unreal Engine, y omite los programas auxiliares habituales.
- **Crea un perfil de juego de MAKO**: copia el perfil predeterminado `mako` en un perfil propio del juego en `conf.toml` y escribe los metadatos de perfil de MAKO. **Tanto MAKO UI como el plugin de Decky ven este perfil y pueden editarlo directamente.**
- **Evita asociaciones duplicadas**: si el perfil predeterminado `mako` también está asociado al ejecutable de este juego, el ejecutable se quita de `mako`, para que el juego use solo su propio perfil. Si el perfil de otro juego está asociado al mismo ejecutable, verás un aviso, pero no se cambia nada automáticamente.

### 3. Cómo se escriben las opciones de lanzamiento

Steam solo lee las opciones de lanzamiento al iniciarse y sobrescribe su archivo de configuración al cerrarse. Para que Steam no sobrescriba tu cambio, el Asistente MAKO elige el método de escritura según el estado de Steam y muestra ese estado en la ventana:

| Estado de Steam | Método de escritura |
|---|---|
| Cerrado | Edita directamente el `localconfig.vdf` de Steam (tras hacer una copia de seguridad) |
| Abierto y con acceso al cliente de Steam (requiere Decky Loader) | Aplica el cambio en directo a través del cliente de Steam, sin reiniciar Steam |
| Abierto, pero sin acceso al cliente | Pregunta si quieres cerrar Steam → aplica el cambio → vuelve a abrir Steam |

### 4. Eliminar

- «Eliminar» solo quita `mako-launch` de las opciones de lanzamiento y deja tus demás opciones como estaban.
- Los ajustes de MAKO del juego se **conservan de forma predeterminada**, para que puedas reutilizarlos si vuelves a instalarlo más adelante. Marca «Eliminar también los ajustes de MAKO Renderer del juego» para borrarlos también.

### 5. Importar ajustes existentes

Si ya habías añadido `mako-launch` a un juego a mano, ese juego muestra el botón «Importar ajustes». Al pulsarlo se crea el perfil de MAKO del juego y, a partir de entonces, se incluye en la actualización automática de rutas.

### 6. Actualización automática de rutas tras actualizar un juego

- En cada nuevo escaneo, la herramienta vuelve a detectar los ejecutables de los juegos **instalados con esta herramienta**. Si una actualización movió o renombró el ejecutable, los procesos asociados de MAKO se actualizan automáticamente y el cambio aparece en el área de registro.
- Los procesos asociados que **añadiste a mano** en MAKO UI se conservan.
- Si borraste el perfil de un juego en MAKO UI, la herramienta respeta esa decisión y no lo vuelve a crear.
- Si una biblioteca está temporalmente desconectada (por ejemplo, un disco externo sin conectar), los ajustes de esos juegos no cambian.

### 7. Iniciar juegos desde la lista

Cada fila tiene un botón «▶ Jugar» que inicia el juego a través de Steam. Mientras el juego está en ejecución, el botón muestra «En ejecución».

### 8. Vista en directo de las funciones de MAKO que se están usando

La columna «Funciones MAKO activas» se actualiza cada 3 segundos. Muestra lo que MAKO **ha aplicado realmente** dentro del juego, no lo que dice el archivo de configuración:

- **Generación de fotogramas**: multiplicador fijo (por ejemplo ×2) o modo adaptativo (FPS objetivo y multiplicador máximo), escala Flow y modo de rendimiento.
- **Escalado**: método y resolución (por ejemplo 1280×720 → 2560×1440), y supermuestreo.
- **Otras capas**: vkBasalt, Zink, audio ALSA.
- **Cambios pendientes**, como «hay que reiniciar el juego» o «hay que reconstruir la swapchain», y los errores que informe MAKO.

Si un juego tiene Mako FG instalado pero MAKO no se ha cargado realmente, también se indica, para que puedas localizar el problema.

### 9. Superposición al iniciar un juego

Si el Asistente MAKO está abierto al iniciar un juego, en cuanto detecta que MAKO funciona en él muestra las funciones de MAKO activas en la esquina inferior derecha durante unos 10 segundos y luego se desvanece:

- Aparece una vez por inicio, nunca toma el foco del teclado ni del ratón, y los clics del ratón la atraviesan.
- Puede mostrarse encima de juegos de Proton a pantalla completa.
- Si un juego con Mako FG instalado sigue sin cargar MAKO 90 segundos después de iniciarse, se muestra un aviso en su lugar.
- Puedes desactivarla con la casilla «Superposición al iniciar» de la barra de herramientas.

### 10. Búsqueda y filtros

- Busca por nombre del juego (en cualquier idioma) o por App ID.
- Filtros: todos los juegos, con Mako FG, sin Mako FG, solo ajustes de MAKO, en ejecución.

### 11. Doce idiomas de interfaz

台灣正體中文, 简体中文, English, 日本語, Deutsch, Français, Español, Italiano, ไทย, Tiếng Việt, Bahasa Melayu, हिन्दी.

La primera vez, el idioma sigue al del sistema. Puedes cambiarlo en cualquier momento arriba a la derecha; el cambio se aplica al instante y se recuerda.

### 12. Pensado para ser seguro

- Antes de cada cambio se hace una copia de seguridad de `conf.toml` y del `localconfig.vdf` de Steam (`*.mako-assistant.bak`).
- Después de escribir `conf.toml`, la herramienta lo comprueba con `mako-cli validate`. Si MAKO lo rechaza, el archivo original se restaura automáticamente.
- `localconfig.vdf` nunca se edita directamente mientras Steam está abierto.

## Instalar el Asistente MAKO

**AppImage (recomendado)**: incluye Python y Qt, así que no hay que instalar nada más.

```bash
chmod +x MAKO_Assistant-*-x86_64.AppImage
./MAKO_Assistant-*-x86_64.AppImage
```

**Desde el código fuente**: requiere Python 3.11 o posterior y PyQt6 (Arch: `sudo pacman -S python-pyqt6`).

```bash
./mako-assistant    # ejecutar directamente
./install.sh        # instalar en ~/.local/share/mako-assistant y añadir una entrada al menú de aplicaciones
```

## Limitaciones conocidas

- **La superposición no aparece en el modo Juego de Steam Deck (gamescope).** En Steam Deck, usa el plugin de Decky de MAKO.
- Los juegos en pantalla completa exclusiva con Wayland nativo pueden tapar la superposición.
- Las opciones de lanzamiento solo se pueden cambiar en directo a través del puerto del cliente de Steam que abre Decky Loader (8080). Sin Decky, cierra Steam antes de aplicar o deja que la herramienta cierre y vuelva a abrir Steam.
- La vista de funciones realmente activas y los metadatos de perfil de MAKO se leen en el formato de la versión actual de MAKO. Tras una actualización importante de MAKO o de Steam, puede que dejen de mostrarse temporalmente (verás «—»), pero instalar y eliminar siguen funcionando.
- En tailandés, vietnamita, malayo e hindi, los menús contextuales están en inglés (Qt no tiene traducciones oficiales para estos idiomas). Steam no tiene nombres de juegos en malayo ni en hindi, así que estos dos idiomas muestran siempre los nombres originales.
- Solo se conserva la copia de seguridad más reciente.

## Dónde se guardan los datos

| Ubicación | Contenido |
|---|---|
| `~/.config/mako-assistant/state.json` | Estado propio del Asistente MAKO: caché de la lista de juegos, juegos instalados con esta herramienta, idioma de la interfaz, ajuste de la superposición |
| `~/.config/mako-render/conf.toml` | Ajustes de MAKO Renderer (perfiles de juego) |
| `~/.config/mako-render/profile-metadata.json` | Metadatos de los perfiles de MAKO (nombres de juegos, App ID de Steam) |
| `<Steam>/userdata/<ID de usuario>/config/localconfig.vdf` | Opciones de lanzamiento de Steam |
