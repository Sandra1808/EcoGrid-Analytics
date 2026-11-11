package EcoGrid.Backend.rest;

import EcoGrid.Backend.dao.ComunidadautonomaRepository;
import EcoGrid.Backend.dto.CcaaResponse;
import EcoGrid.Backend.dto.DemandaHistoricaResponse;
import EcoGrid.Backend.service.DemandaHistoricaService;
import org.springframework.data.domain.Sort;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.List;

@RestController
public class EcoGridController {

    private final ComunidadautonomaRepository comunidadRepository;
    private final DemandaHistoricaService demandaHistoricaService;

    public EcoGridController(
            ComunidadautonomaRepository comunidadRepository,
            DemandaHistoricaService demandaHistoricaService) {
        this.comunidadRepository = comunidadRepository;
        this.demandaHistoricaService = demandaHistoricaService;
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
            @RequestParam(defaultValue = "1") Long ccaaId,
            @RequestParam
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant desde,
            @RequestParam
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant hasta) {
        return demandaHistoricaService.buscar(ccaaId, desde, hasta);
    }

    public record HealthResponse(String status, String message) {
    }
}