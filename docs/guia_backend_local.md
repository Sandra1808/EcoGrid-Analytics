# Guía para arrancar la API de EcoGrid en local

Le comparto esta guía para ejecutar la API de EcoGrid en su ordenador y conectarla a la base de datos Oracle mediante la wallet que le facilitaré por separado.

## Qué le proporcionaré

- El JAR ejecutable de Spring Boot.  
- El ZIP de la wallet de Oracle y su contraseña, por canales privados.  
- El usuario de base de datos `ECOGRID` y su contraseña, por un canal privado.  
- Los valores de `TENANT_CIF` y `PREDICTIONS_API_KEY`, por un canal privado.

La wallet y las credenciales no están incluidas en el repositorio ni en el JAR. No es necesario instalar Oracle Database ni Oracle Client.

## Requisitos

- Windows y PowerShell.  
- Java 17 instalado.  
- Conexión a Internet y permiso de red para alcanzar la instancia Oracle. Si la instancia restringe el acceso por IP, habrá que autorizar la IP pública desde la que se conectará.  
- El ZIP de la wallet recibido por privado.

Compruebe Java desde PowerShell:

```powershell
java -version
```

&nbsp;

Debe indicar la versión 17\.

## Configuración y arranque

1. Guarde el JAR en una ubicación local. Descargue y extraiga el ZIP de la wallet fuera del repositorio, por ejemplo:

```
C:\EcoGrid\backend-0.0.1-SNAPSHOT.jar
C:\Oracle\EcoGrid\Wallet\
```

La carpeta extraída que indique `TNS_ADMIN` debe contener los archivos de configuración de la wallet, como `tnsnames.ora` y `sqlnet.ora`. Para la API no se usa el comando `SET CLOUDCONFIG` de SQLcl.

2. Abra PowerShell en `C:\EcoGrid` y configure las variables de entorno con los valores que le proporcionaré. En el ejemplo se utiliza el alias `ecogriddb_high`.

```powershell
$env:SPRING_DATASOURCE_URL = 'jdbc:oracle:thin:@ecogriddb_high?TNS_ADMIN=C:\Oracle\EcoGrid\Wallet'
$env:SPRING_DATASOURCE_USERNAME = 'ECOGRID'
$env:SPRING_DATASOURCE_PASSWORD = '<CONTRASEÑA_ORACLE>'
$env:TENANT_CIF = '<CIF_CONFIGURADO>'
$env:PREDICTIONS_API_KEY = '<CLAVE_API_PREDICCIONES>'
```

Las variables solo se aplican a esta ventana de PowerShell. No las publique ni las añada al repositorio. La URL debe apuntar a la carpeta extraída de la wallet. Si el alias indicado no coincide con el que acordemos, sustitúyalo por el alias exacto.

3. En esa misma ventana, arranque la API:

```powershell
java -jar .\backend-0.0.1-SNAPSHOT.jar
```

Si el JAR recibido tiene otro nombre, sustituya el nombre del comando por el nombre real del archivo.

4. Mantenga la ventana abierta mientras utilice el dashboard. Para detener la API, pulse **Ctrl+C**.

## Comprobación

Con la API en marcha, abra esta dirección:

```
http://localhost:8080/api/health
```

La respuesta esperada es un JSON con estado `UP`. Esta comprobación confirma que la API responde; para confirmar también la conexión a Oracle, revise que el arranque no muestre errores de conexión y consulte una función de la API que lea datos de la base de datos. Después, el dashboard se puede abrir con Live Server en `http://localhost:5500`. Para que el navegador pueda comunicarse con la API, Spring debe permitir ese origen CORS y las peticiones con credenciales.

## Alternativa: ejecutar el proyecto desde IntelliJ IDEA

Si el JAR no funciona, también se puede arrancar el código fuente del backend:

1. Instale IntelliJ IDEA y Java 17\. Abra en IntelliJ la carpeta del backend que contiene `pom.xml` (por ejemplo, `src\api\backend`) y espere a que termine la importación de Maven.  
2. Compruebe que el SDK del proyecto está configurado como Java 17\.  
3. Localice la clase principal del backend, identificada con `@SpringBootApplication`, y selecciónela como clase de la configuración de ejecución de IntelliJ.  
4. Abra **Run \> Edit Configurations** y añada estas variables en **Environment variables**. Use los mismos valores proporcionados para ejecutar el JAR; complete la ruta de la wallet con la ubicación local:

   SPRING\_DATASOURCE\_URL=jdbc:oracle:thin:@\<ALIAS\_CONFIRMADO\>?TNS\_ADMIN=\<RUTA\_LOCAL\_DE\_LA\_WALLET\>  
   SPRING\_DATASOURCE\_USERNAME=ECOGRID  
   SPRING\_DATASOURCE\_PASSWORD=\<CONTRASEÑA\_ORACLE\>  
   TENANT\_CIF=\<CIF\_CONFIGURADO\>  
   PREDICTIONS\_API\_KEY=\<CLAVE\_API\_PREDICCIONES\>

&nbsp;&nbsp;En IntelliJ, introduzca cada variable como un par nombre/valor en el editor de variables de entorno. No escriba las contraseñas en archivos del proyecto ni las suba a GitHub.

5. Inicie la configuración con el botón verde. La API debería quedar disponible en `http://localhost:8080`; se puede comprobar en `http://localhost:8080/api/health`.

## Comprobación

Con la API en marcha, abra esta dirección:

http\://localhost:8080/api/health

La respuesta esperada es un JSON con estado `UP`. Esta comprobación confirma que la API responde; para confirmar también la conexión a Oracle, revise que el arranque no muestre errores de conexión y consulte una función de la API que lea datos de la base de datos. Después, el dashboard se puede abrir con Live Server en `http://localhost:5500`. Para que el navegador pueda comunicarse con la API, Spring debe permitir ese origen CORS y las peticiones con credenciales.

## Cómo prepararé el JAR

En mi ordenador, generaré el JAR desde la carpeta del backend, donde está `mvnw.cmd`:

.\\mvnw.cmd clean package \-DskipTests

El resultado se guarda en `target`. Comprobaré el nombre exacto antes de entregarlo. El JAR no contiene la wallet ni las credenciales.

## Si la API no arranca

* Si PowerShell no reconoce `java`, instale Java 17 y compruebe que está disponible en `PATH`.  
* Si aparece un error de Oracle o de wallet, verifique `SPRING_DATASOURCE_URL`, el alias, la ruta de `TNS_ADMIN` y las credenciales recibidas.  
* Si SQLcl conecta pero la API no, confirme que la URL JDBC usa el alias y la ruta de la wallet correctos; la configuración `SET CLOUDCONFIG` de SQLcl no configura Spring Boot.  
* Si el dashboard no puede consultar la API, compruebe que Spring sigue ejecutándose en el puerto `8080` y que CORS permite `http://localhost:5500`.  
* Si el inicio de sesión devuelve `401`, habrá que verificar que el usuario de prueba y su contraseña estén configurados correctamente en Oracle.

&nbsp;

&nbsp;