package EcoGrid.service;

import EcoGrid.dao.AlertasOperativaRepository;
import EcoGrid.dao.ComunidadautonomaRepository;
import EcoGrid.dao.DemandageneracionreeRepository;
import EcoGrid.dao.ImpactodesviacioneRepository;
import EcoGrid.dao.PrediccionesdemandaRepository;
import EcoGrid.dto.DashboardKpisDto;
import EcoGrid.dto.DashboardPointDto;
import EcoGrid.dto.DashboardSummaryDto;
import EcoGrid.dto.DemandaHistoricaDto;
import EcoGrid.dto.DemandaSerieDto;
import EcoGrid.entity.AlertasOperativa;
import EcoGrid.entity.Prediccionesdemanda;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.Comparator;
import java.util.Map;
import java.util.TreeMap;

@Service
public class DashboardService {

    private static final ZoneId ZONA_ESPANA = ZoneId.of("Europe/Madrid");

    private final DemandaHistoricaService demandaHistoricaService;
    private final DemandageneracionreeRepository demandaRepository;
    private final PrediccionesdemandaRepository prediccionesRepository;
    private final ImpactodesviacioneRepository impactosRepository;
    private final AlertasOperativaRepository alertasRepository;
    private final ComunidadautonomaRepository comunidadesRepository;

    public DashboardService(
            DemandaHistoricaService demandaHistoricaService,
            DemandageneracionreeRepository demandaRepository,
            PrediccionesdemandaRepository prediccionesRepository,
            ImpactodesviacioneRepository impactosRepository,
            AlertasOperativaRepository alertasRepository,
            ComunidadautonomaRepository comunidadesRepository) {
        this.demandaHistoricaService = demandaHistoricaService;
        this.demandaRepository = demandaRepository;
        this.prediccionesRepository = prediccionesRepository;
        this.impactosRepository = impactosRepository;
        this.alertasRepository = alertasRepository;
        this.comunidadesRepository = comunidadesRepository;
    }

    @Transactional(readOnly = true)
    public DashboardSummaryDto resumen(LocalDate fecha, Long ccaaId) {
        var comunidad = comunidadesRepository.findById(ccaaId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.BAD_REQUEST,
                        "No existe la CCAA indicada"));

        Instant desde = fecha.atStartOfDay(ZONA_ESPANA).toInstant();
        Instant hastaExclusivo = fecha.plusDays(1)
                .atStartOfDay(ZONA_ESPANA)
                .toInstant();
        Instant hasta = hastaExclusivo.minusSeconds(1);

        var serie = serie(ccaaId, desde, hasta);

        BigDecimal suma = BigDecimal.ZERO;
        int cantidad = 0;

        for (DemandaSerieDto punto : serie) {
            if (punto.demandaRealMwh() != null) {
                suma = suma.add(punto.demandaRealMwh());
                cantidad++;
            }
        }

        BigDecimal demandaMedia = cantidad == 0
                ? null
                : suma.divide(BigDecimal.valueOf(cantidad), 2, RoundingMode.HALF_UP);

        LocalDateTime desdeDb = LocalDateTime.ofInstant(desde, ZoneOffset.UTC);
        LocalDateTime hastaDb = LocalDateTime.ofInstant(hasta, ZoneOffset.UTC);

        BigDecimal costeDesvio = impactosRepository.sumarCosteDesvio(
                ccaaId, desdeDb, hastaDb);

        var alertas = alertasRepository
                .findByIdtiempo_FechoraBetweenOrderByIdtiempo_FechoraDesc(
                        desdeDb, hastaDb);

        String nivelGlobal = alertas.stream()
                .map(AlertasOperativa::getNivelalerta)
                .filter(nivel -> nivel != null && !nivel.isBlank())
                .max(Comparator.comparingInt(this::prioridadAlerta))
                .orElse("NORMAL");

        var serieResumen = serie.stream()
                .map(punto -> new DashboardPointDto(
                        punto.fecHora(),
                        punto.demandaRealMwh()))
                .toList();

        return new DashboardSummaryDto(
                fecha,
                comunidad.getCodine(),
                new DashboardKpisDto(demandaMedia, costeDesvio, nivelGlobal),
                serieResumen
        );
    }

    @Transactional(readOnly = true)
    public java.util.List<DemandaSerieDto> serie(
            Long ccaaId, Instant desde, Instant hasta) {

        if (desde == null || hasta == null || desde.isAfter(hasta)) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "El intervalo de fechas no es válido");
        }

        Map<Instant, PuntoMutable> puntos = new TreeMap<>();

        for (DemandaHistoricaDto dato :
                demandaHistoricaService.buscar(ccaaId, desde, hasta)) {
            PuntoMutable punto = puntos.computeIfAbsent(
                    dato.fechaHora(), ignored -> new PuntoMutable());
            punto.demandaReal = dato.demandaRealMw();
        }

        LocalDateTime desdeDb = LocalDateTime.ofInstant(desde, ZoneOffset.UTC);
        LocalDateTime hastaDb = LocalDateTime.ofInstant(hasta, ZoneOffset.UTC);

        for (Prediccionesdemanda prediccion :
                prediccionesRepository
                        .findByIdccaa_IdAndIdtiempo_FechoraBetweenOrderByIdtiempo_FechoraAsc(
                                ccaaId, desdeDb, hastaDb)) {
            Instant fechaHora = prediccion.getIdtiempo()
                    .getFechora()
                    .toInstant(ZoneOffset.UTC);

            PuntoMutable punto = puntos.computeIfAbsent(
                    fechaHora, ignored -> new PuntoMutable());
            punto.demandaPredicha = prediccion.getDemandapredichamw();
        }

        return puntos.entrySet().stream()
                .map(entry -> {
                    BigDecimal real = entry.getValue().demandaReal;
                    BigDecimal predicha = entry.getValue().demandaPredicha;
                    BigDecimal desviacion = real == null || predicha == null
                            ? null
                            : real.subtract(predicha);

                    return new DemandaSerieDto(
                            entry.getKey(), real, predicha, desviacion);
                })
                .toList();
    }

    private int prioridadAlerta(String nivel) {
        return switch (nivel.toUpperCase()) {
            case "CRITICA", "CRÍTICA", "CRITICO", "CRÍTICO" -> 4;
            case "ALTO" -> 3;
            case "MEDIO" -> 2;
            case "BAJO" -> 1;
            default -> 0;
        };
    }

    private static class PuntoMutable {
        private BigDecimal demandaReal;
        private BigDecimal demandaPredicha;
    }
}