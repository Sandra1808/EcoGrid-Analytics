package EcoGrid.Backend.service;

import EcoGrid.Backend.dao.DemandageneracionreeRepository;
import EcoGrid.Backend.dto.DemandaHistoricaResponse;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.List;

@Service
public class DemandaHistoricaService {

    private final DemandageneracionreeRepository repository;

    public DemandaHistoricaService(DemandageneracionreeRepository repository) {
        this.repository = repository;
    }

    @Transactional(readOnly = true)
    public List<DemandaHistoricaResponse> buscar(
            Long ccaaId, Instant desde, Instant hasta) {

        if (desde.isAfter(hasta)) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "'desde' debe ser anterior o igual a 'hasta'");
        }

        LocalDateTime desdeOracle = LocalDateTime.ofInstant(desde, ZoneOffset.UTC);
        LocalDateTime hastaOracle = LocalDateTime.ofInstant(hasta, ZoneOffset.UTC);

        return repository
                .findByIdccaa_IdAndIdtiempo_FechoraBetweenOrderByIdtiempo_FechoraAsc(
                        ccaaId, desdeOracle, hastaOracle)
                .stream()
                .map(d -> new DemandaHistoricaResponse(
                        d.getIdtiempo().getFechora().toInstant(ZoneOffset.UTC),
                        d.getDemandarealmw(),
                        d.getDemandaprevistareemw(),
                        d.getDemandaprogramadamw(),
                        d.getDemandaprogramadatotalmw()))
                .toList();
    }
}