package EcoGrid.rest;

import EcoGrid.dao.ComunidadautonomaRepository;
import EcoGrid.dto.AlertasOperativaDto;
import EcoGrid.dto.CcaaDto;
import EcoGrid.dto.DashboardSummaryDto;
import EcoGrid.dto.DemandaHistoricaDto;
import EcoGrid.dto.DemandaSerieDto;
import EcoGrid.dto.FuenteDto;
import EcoGrid.dto.PrediccionDto;
import EcoGrid.dto.PrediccionLoteDto;
import EcoGrid.dto.RawFileDto;
import EcoGrid.dto.SchedulerTaskDto;
import EcoGrid.dto.UsuarioResponse;
import EcoGrid.service.AlertasOperativaService;
import EcoGrid.service.DashboardService;
import EcoGrid.service.DemandaHistoricaService;
import EcoGrid.service.FuentesService;
import EcoGrid.service.PrediccionesService;
import EcoGrid.service.UsuariosService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Sort;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
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
import java.util.List;
import java.util.Map;
import java.time.ZoneId;

@RestController
public class EcoGridController {

    private final ComunidadautonomaRepository comunidadRepository;
    private final DemandaHistoricaService demandaHistoricaService;
    private final PrediccionesService prediccionesService;
    private final AlertasOperativaService alertasOperativaService;
    private final DashboardService dashboardService;
    private final FuentesService fuentesService;
    private final UsuariosService usuariosService;

    @Value("${app.predictions.api-key:}")
    private String predictionApiKey;

    public EcoGridController(
            ComunidadautonomaRepository comunidadRepository,
            DemandaHistoricaService demandaHistoricaService,
            PrediccionesService prediccionesService,
            AlertasOperativaService alertasOperativaService,
            DashboardService dashboardService,
            FuentesService fuentesService,
            UsuariosService usuariosService) {
        this.comunidadRepository = comunidadRepository;
        this.demandaHistoricaService = demandaHistoricaService;
        this.prediccionesService = prediccionesService;
        this.alertasOperativaService = alertasOperativaService;
        this.dashboardService = dashboardService;
        this.fuentesService = fuentesService;
        this.usuariosService = usuariosService;
    }

    @GetMapping("/api/health")
    public HealthResponse health() {
        return new HealthResponse("UP", "EcoGrid API funcionando");
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

    public record HealthResponse(String status, String message) {
    }
}