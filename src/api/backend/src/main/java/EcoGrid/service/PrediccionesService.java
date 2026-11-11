package EcoGrid.service;

import EcoGrid.dao.ComunidadautonomaRepository;
import EcoGrid.dao.FestivosboeRepository;
import EcoGrid.dao.ModelosmlRepository;
import EcoGrid.dao.PrediccionesdemandaRepository;
import EcoGrid.dao.TiempohorarioRepository;
import EcoGrid.dto.PrediccionLoteRequest;
import EcoGrid.dto.PrediccionResponse;
import EcoGrid.entity.Comunidadautonoma;
import EcoGrid.entity.Modelosml;
import EcoGrid.entity.Prediccionesdemanda;
import EcoGrid.entity.Tiempohorario;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class PrediccionesService {

    private static final Long ID_ESPANA = 1L;
    private static final DateTimeFormatter ID_FORMAT =
            DateTimeFormatter.ofPattern("yyyyMMddHH");

    private final PrediccionesdemandaRepository prediccionesRepository;
    private final TiempohorarioRepository tiempoRepository;
    private final FestivosboeRepository festivosRepository;
    private final ModelosmlRepository modelosRepository;
    private final ComunidadautonomaRepository comunidadesRepository;

    public PrediccionesService(
            PrediccionesdemandaRepository prediccionesRepository,
            TiempohorarioRepository tiempoRepository,
            FestivosboeRepository festivosRepository,
            ModelosmlRepository modelosRepository,
            ComunidadautonomaRepository comunidadesRepository) {
        this.prediccionesRepository = prediccionesRepository;
        this.tiempoRepository = tiempoRepository;
        this.festivosRepository = festivosRepository;
        this.modelosRepository = modelosRepository;
        this.comunidadesRepository = comunidadesRepository;
    }

    @Transactional
    public int guardarLote(PrediccionLoteRequest request) {
        Modelosml modelo = modelosRepository.findById(request.modeloId())
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.BAD_REQUEST, "El modelo indicado no existe"));

        if (!Boolean.TRUE.equals(modelo.getIndactivo())) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT, "El modelo indicado no está activo");
        }

        Comunidadautonoma espana = comunidadesRepository.findById(ID_ESPANA)
                .orElseThrow(() -> new IllegalStateException(
                        "No existe la comunidad nacional IDCCAA=1"));

        Instant primeraHora = request.predicciones().get(0).fechaHora();
        Map<LocalDate, Boolean> festivosCache = new HashMap<>();

        for (int i = 0; i < request.predicciones().size(); i++) {
            var punto = request.predicciones().get(i);
            Instant esperada = primeraHora.plusSeconds(i * 3600L);

            if (!punto.fechaHora().equals(esperada)) {
                throw new ResponseStatusException(
                        HttpStatus.BAD_REQUEST,
                        "Las 24 predicciones deben ser horas consecutivas y ordenadas");
            }

            LocalDateTime fechaHora = LocalDateTime.ofInstant(
                    punto.fechaHora(), ZoneOffset.UTC);

            if (fechaHora.getMinute() != 0
                    || fechaHora.getSecond() != 0
                    || fechaHora.getNano() != 0) {
                throw new ResponseStatusException(
                        HttpStatus.BAD_REQUEST,
                        "Cada fechaHora debe estar alineada al inicio de una hora UTC");
            }

            Long idTiempo = Long.valueOf(fechaHora.format(ID_FORMAT));
            Tiempohorario tiempo = tiempoRepository.findById(idTiempo)
                    .orElseGet(() -> crearTiempo(fechaHora, idTiempo, festivosCache));

            Prediccionesdemanda prediccion =
                    prediccionesRepository
                            .findByIdmodelo_IdAndIdccaa_IdAndIdtiempo_Id(
                                    modelo.getId(), ID_ESPANA, idTiempo)
                            .orElseGet(Prediccionesdemanda::new);

            prediccion.setIdmodelo(modelo);
            prediccion.setIdccaa(espana);
            prediccion.setIdtiempo(tiempo);
            prediccion.setDemandapredichamw(punto.demandaPredichaMw());
            prediccion.setDemandabaselinemw(punto.demandaBaselineMw());
            prediccion.setFecha(Instant.now());

            prediccionesRepository.save(prediccion);
        }

        return request.predicciones().size();
    }

    @Transactional(readOnly = true)
    public List<PrediccionResponse> listarNacional(Instant desde, Instant hasta) {
        if (desde.isAfter(hasta)) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "'desde' debe ser anterior o igual a 'hasta'");
        }

        LocalDateTime desdeDb = LocalDateTime.ofInstant(desde, ZoneOffset.UTC);
        LocalDateTime hastaDb = LocalDateTime.ofInstant(hasta, ZoneOffset.UTC);

        return prediccionesRepository
                .findByIdccaa_IdAndIdtiempo_FechoraBetweenOrderByIdtiempo_FechoraAsc(
                        ID_ESPANA, desdeDb, hastaDb)
                .stream()
                .map(p -> new PrediccionResponse(
                        p.getIdtiempo().getFechora().toInstant(ZoneOffset.UTC),
                        p.getDemandapredichamw(),
                        p.getDemandabaselinemw()))
                .toList();
    }

    private Tiempohorario crearTiempo(
            LocalDateTime fechaHora,
            Long idTiempo,
            Map<LocalDate, Boolean> festivosCache) {
        LocalDate fecha = fechaHora.toLocalDate();
        int diaSemana = fecha.getDayOfWeek().getValue();
        boolean finDeSemana = diaSemana >= 6;
        boolean festivo = festivosCache.computeIfAbsent(
                fecha,
                dia -> festivosRepository.existsByFechaAndAmbitoIgnoreCase(
                        dia, "Nacional"));

        Tiempohorario tiempo = new Tiempohorario();
        tiempo.setId(idTiempo);
        tiempo.setFechora(fechaHora);
        tiempo.setFecha(fecha);
        tiempo.setHora((short) fechaHora.getHour());
        tiempo.setDiasemana(diaSemana);
        tiempo.setMes((short) fechaHora.getMonthValue());
        tiempo.setYear((short) fechaHora.getYear());
        tiempo.setIndfinsemana(finDeSemana);
        tiempo.setIndfestivo(festivo);

        return tiempoRepository.save(tiempo);
    }
}