package EcoGrid.rest;

import EcoGrid.dao.ComunidadautonomaRepository;
import EcoGrid.dto.CcaaResponse;
import EcoGrid.dto.DemandaHistoricaResponse;
import EcoGrid.dto.PrediccionLoteRequest;
import EcoGrid.dto.PrediccionResponse;
import EcoGrid.service.DemandaHistoricaService;
import EcoGrid.service.PrediccionesService;
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
import java.util.List;
import java.util.Map;

@RestController
public class EcoGridController {

    private final ComunidadautonomaRepository comunidadRepository;
    private final DemandaHistoricaService demandaHistoricaService;
    private final PrediccionesService prediccionesService;

    @Value("${app.predictions.api-key:}")
    private String predictionApiKey;

    public EcoGridController(
            ComunidadautonomaRepository comunidadRepository,
            DemandaHistoricaService demandaHistoricaService,
            PrediccionesService prediccionesService) {
        this.comunidadRepository = comunidadRepository;
        this.demandaHistoricaService = demandaHistoricaService;
        this.prediccionesService = prediccionesService;
    }

    @GetMapping("/api/health")
    public HealthResponse health() {
        return new HealthResponse("UP", "EcoGrid API funcionando");
    }

    @GetMapping("/api/comunidades")
    public List<CcaaResponse> listarComunidades() {
        return comunidadRepository.findAll(Sort.by("nombreccaa"))
                .stream()
                .map(ccaa -> new CcaaResponse(
                        ccaa.getId(),
                        ccaa.getCodine(),
                        ccaa.getNombreccaa()))
                .toList();
    }

    @GetMapping("/api/demanda/historica")
    public List<DemandaHistoricaResponse> listarDemandaHistorica(
            @RequestParam(name = "ccaaId", defaultValue = "1") Long ccaaId,
            @RequestParam(name = "desde")
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant desde,
            @RequestParam(name = "hasta")
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant hasta) {
        return demandaHistoricaService.buscar(ccaaId, desde, hasta);
    }

    @PostMapping("/api/predicciones/lote")
    public Map<String, Integer> recibirPredicciones(
            @RequestHeader(name = "X-API-Key", required = false) String apiKey,
            @Valid @RequestBody PrediccionLoteRequest request) {
        validarApiKey(apiKey);
        return Map.of("guardadas", prediccionesService.guardarLote(request));
    }

    @GetMapping("/api/predicciones/nacional")
    public List<PrediccionResponse> prediccionesNacionales(
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
                    HttpStatus.UNAUTHORIZED, "API key no válida");
        }
    }

    public record HealthResponse(String status, String message) {
    }
}