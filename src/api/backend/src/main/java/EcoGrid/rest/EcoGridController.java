package EcoGrid.rest;

import EcoGrid.dao.ComunidadautonomaRepository;
import EcoGrid.dao.ModelosmlRepository;
import EcoGrid.dao.UsuarioRepository;
import EcoGrid.dto.*;
import EcoGrid.entity.Usuario;
import EcoGrid.service.AlertasOperativaService;
import EcoGrid.service.DashboardService;
import EcoGrid.service.DemandaHistoricaService;
import EcoGrid.service.FuentesService;
import EcoGrid.service.PrediccionesService;
import EcoGrid.service.UsuariosService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Sort;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.context.SecurityContextRepository;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.List;
import java.util.Map;

@RestController
public class EcoGridController {

    private static final Logger log =
            LoggerFactory.getLogger(EcoGridController.class);

    private final ComunidadautonomaRepository comunidadRepository;
    private final ModelosmlRepository modelosmlRepository;
    private final DemandaHistoricaService demandaHistoricaService;
    private final PrediccionesService prediccionesService;
    private final AlertasOperativaService alertasOperativaService;
    private final DashboardService dashboardService;
    private final FuentesService fuentesService;
    private final UsuariosService usuariosService;
    private final UsuarioRepository usuarioRepository;
    private final AuthenticationManager authenticationManager;
    private final SecurityContextRepository securityContextRepository;
    private final String tenantCif;

    @Value("${app.predictions.api-key:}")
    private String predictionApiKey;

    public EcoGridController(
            ComunidadautonomaRepository comunidadRepository,
            ModelosmlRepository modelosmlRepository,
            DemandaHistoricaService demandaHistoricaService,
            PrediccionesService prediccionesService,
            AlertasOperativaService alertasOperativaService,
            DashboardService dashboardService,
            FuentesService fuentesService,
            UsuariosService usuariosService,
            UsuarioRepository usuarioRepository,
            AuthenticationManager authenticationManager,
            SecurityContextRepository securityContextRepository,
            @Value("${app.tenant.cif:}") String tenantCif) {
        this.comunidadRepository = comunidadRepository;
        this.modelosmlRepository = modelosmlRepository;
        this.demandaHistoricaService = demandaHistoricaService;
        this.prediccionesService = prediccionesService;
        this.alertasOperativaService = alertasOperativaService;
        this.dashboardService = dashboardService;
        this.fuentesService = fuentesService;
        this.usuariosService = usuariosService;
        this.usuarioRepository = usuarioRepository;
        this.authenticationManager = authenticationManager;
        this.securityContextRepository = securityContextRepository;
        this.tenantCif = tenantCif;
    }

    @GetMapping("/api/models/active")
    public ModeloActivoDto modeloActivo() {
        var modelo = modelosmlRepository
                .findByIndactivoTrueOrderByFecentrenamientoDesc()
                .stream()
                .findFirst()
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "No hay un modelo activo"));

        return new ModeloActivoDto(
                modelo.getId(),
                modelo.getNombrealgoritmo(),
                modelo.getVersion());
    }

    @GetMapping("/api/health")
    public HealthResponse health() {
        return new HealthResponse("UP", "EcoGrid API funcionando");
    }

    @PostMapping("/api/auth/login")
    public AuthResponse login(
            @Valid @RequestBody LoginRequest login,
            HttpServletRequest request,
            HttpServletResponse response) {
        Authentication authentication;

        try {
            authentication = authenticationManager.authenticate(
                    UsernamePasswordAuthenticationToken.unauthenticated(
                            login.email().trim(),
                            login.password()));
        } catch (AuthenticationException exception) {
            log.warn(
                    "Fallo al autenticar en /api/auth/login ({})",
                    exception.getClass().getSimpleName(),
                    exception);
            SecurityContextHolder.clearContext();
            throw new ResponseStatusException(
                    HttpStatus.UNAUTHORIZED,
                    "Email o contraseña incorrectos");
        }

        HttpSession existingSession = request.getSession(false);
        if (existingSession != null) {
            request.changeSessionId();
        }

        SecurityContext context = SecurityContextHolder.createEmptyContext();
        context.setAuthentication(authentication);
        SecurityContextHolder.setContext(context);
        securityContextRepository.saveContext(context, request, response);

        return getAuthResponse(authentication.getName());
    }

    @GetMapping("/api/auth/me")
    public AuthResponse currentUser(Authentication authentication) {
        return getAuthResponse(authentication.getName());
    }

    @PostMapping("/api/auth/logout")
    public ResponseEntity<Void> logout(HttpServletRequest request) {
        SecurityContextHolder.clearContext();

        HttpSession session = request.getSession(false);
        if (session != null) {
            session.invalidate();
        }

        return ResponseEntity.noContent().build();
    }

    @GetMapping("/api/comunidades")
    public List<CcaaDto> listarComunidades() {
        return comunidadRepository.findAll(Sort.by("nombreccaa"))
                .stream()
                .map(ccaa -> new CcaaDto(
                        ccaa.getId(),
                        ccaa.getCodine(),
                        ccaa.getNombreccaa()))
                .toList();
    }

    @GetMapping("/api/demanda/historica")
    public List<DemandaHistoricaDto> listarDemandaHistorica(
            @RequestParam(name = "ccaaId", defaultValue = "1") Long ccaaId,
            @RequestParam(name = "desde")
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant desde,
            @RequestParam(name = "hasta")
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant hasta) {
        return demandaHistoricaService.buscar(ccaaId, desde, hasta);
    }

    @GetMapping("/api/dashboard/summary")
    public DashboardSummaryDto resumenDashboard(
            @RequestParam(name = "fecha")
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate fecha,
            @RequestParam(name = "ccaaId", defaultValue = "10") Long ccaaId) {
        return dashboardService.resumen(fecha, ccaaId);
    }

    @GetMapping("/api/demand/series")
    public List<DemandaSerieDto> serieDemanda(
            @RequestParam(name = "fecha")
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate fecha,
            @RequestParam(name = "ccaaId", defaultValue = "10") Long ccaaId) {
        Instant desde = fecha.atStartOfDay(ZoneId.of("Europe/Madrid"))
                .toInstant();
        Instant hasta = fecha.plusDays(1)
                .atStartOfDay(ZoneId.of("Europe/Madrid"))
                .toInstant()
                .minusSeconds(1);

        return dashboardService.serie(ccaaId, desde, hasta);
    }

    @GetMapping("/api/alerts")
    public List<AlertasOperativaDto> listarAlertas() {
        return alertasOperativaService.listarTodas();
    }

    @GetMapping("/api/sources")
    public List<FuenteDto> listarFuentes() {
        return fuentesService.listar();
    }

    @GetMapping("/api/raw-files")
    public List<RawFileDto> listarFicherosRaw() {
        return List.of();
    }

    @GetMapping("/api/users")
    public List<UsuarioResponse> listarUsuarios() {
        return usuariosService.listar();
    }

    @GetMapping("/api/scheduler/tasks")
    public List<SchedulerTaskDto> listarTareasProgramadas() {
        return List.of();
    }

    @PostMapping("/api/predicciones/lote")
    public Map<String, Integer> recibirPredicciones(
            @RequestHeader(name = "X-API-Key", required = false) String apiKey,
            @Valid @RequestBody PrediccionLoteDto request) {
        validarApiKey(apiKey);
        return Map.of("guardadas", prediccionesService.guardarLote(request));
    }

    @GetMapping("/api/predicciones/nacional")
    public List<PrediccionDto> prediccionesNacionales(
            @RequestParam(name = "desde")
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant desde,
            @RequestParam(name = "hasta")
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant hasta) {
        return prediccionesService.listarNacional(desde, hasta);
    }

    private AuthResponse getAuthResponse(String email) {
        if (tenantCif.isBlank()) {
            log.warn("La propiedad app.tenant.cif está vacía");
        }

        Usuario usuario = usuarioRepository
                .findByCifAndEmailIgnoreCase(tenantCif, email)
                .orElseThrow(() -> {
                    log.warn(
                            "Usuario autenticado no encontrado para el CIF configurado");
                    return new ResponseStatusException(
                            HttpStatus.UNAUTHORIZED,
                            "Sesión no válida");
                });

        if (!Boolean.TRUE.equals(usuario.getActivo())) {
            log.warn("Login rechazado después de autenticar: usuario inactivo");
            throw new ResponseStatusException(
                    HttpStatus.UNAUTHORIZED,
                    "Sesión no válida");
        }

        return new AuthResponse(
                usuario.getEmail(),
                usuario.getNombre(),
                usuario.getCif(),
                usuario.getIdrol().getRol());
    }

    private void validarApiKey(String recibida) {
        if (predictionApiKey.isBlank()) {
            throw new ResponseStatusException(
                    HttpStatus.SERVICE_UNAVAILABLE,
                    "La ingesta de predicciones no está configurada");
        }

        if (recibida == null || !MessageDigest.isEqual(
                predictionApiKey.getBytes(StandardCharsets.UTF_8),
                recibida.getBytes(StandardCharsets.UTF_8))) {
            throw new ResponseStatusException(
                    HttpStatus.UNAUTHORIZED,
                    "API key no válida");
        }
    }

    public record LoginRequest(
            @NotBlank @Email String email,
            @NotBlank String password) {
    }

    public record AuthResponse(
            String email,
            String nombre,
            String cif,
            String rol) {
    }

    public record HealthResponse(String status, String message) {
    }
}