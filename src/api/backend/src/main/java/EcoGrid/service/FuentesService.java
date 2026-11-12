package EcoGrid.service;

import EcoGrid.dao.DemandageneracionreeRepository;
import EcoGrid.dao.MeteorologiaRepository;
import EcoGrid.dao.PreciosmercadoomieRepository;
import EcoGrid.dto.FuenteDto;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class FuentesService {

    private final DemandageneracionreeRepository demandaRepository;
    private final PreciosmercadoomieRepository preciosRepository;
    private final MeteorologiaRepository meteorologiaRepository;

    public FuentesService(
            DemandageneracionreeRepository demandaRepository,
            PreciosmercadoomieRepository preciosRepository,
            MeteorologiaRepository meteorologiaRepository) {
        this.demandaRepository = demandaRepository;
        this.preciosRepository = preciosRepository;
        this.meteorologiaRepository = meteorologiaRepository;
    }

    @Transactional(readOnly = true)
    public List<FuenteDto> listar() {
        long demanda = demandaRepository.count();
        long precios = preciosRepository.count();
        long meteorologia = meteorologiaRepository.count();

        return List.of(
                crearFuente("REE", demanda),
                crearFuente("OMIE", precios),
                crearFuente("Meteorología", meteorologia)
        );
    }

    private FuenteDto crearFuente(String nombre, long registros) {
        return new FuenteDto(
                nombre,
                registros > 0 ? "Con datos" : "Sin datos",
                registros
        );
    }
}